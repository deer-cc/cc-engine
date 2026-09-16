from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json
import os
from pathlib import Path
from datetime import datetime

# ─── 路径配置 ───────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CONV_DIR = BASE_DIR / "conversations"
CONFIG_FILE = BASE_DIR / "config.json"

app = FastAPI(
    title="客服引擎 v1.0",
    description="智能客服对话系统 — 作品集项目",
    version="1.0.0"
)


# ─── 数据模型 ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    stream: bool = False


class ChatResponse(BaseModel):
    reply: str
    intent: str
    confidence: float
    session_id: str
    turn_count: int


class IntentRequest(BaseModel):
    message: str


class IntentResponse(BaseModel):
    intent: str
    confidence: float
    labels: dict


class KBSearchRequest(BaseModel):
    query: str
    top_k: int = 3


class KBSearchResponse(BaseModel):
    results: List[dict]
    query: str
    count: int


# ─── 初始化 ────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {
        "llm_base_url": os.getenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:15721"),
        "llm_api_key": os.getenv("ANTHROPIC_AUTH_TOKEN", "PROXY_MANAGED"),
        "llm_model": os.getenv("LLM_MODEL", "claude-opus-4-8-20251101"),
        "max_turns": 10,
        "history_window": 6,
        "kb_top_k": 3,
    }


def load_conversations() -> dict:
    """加载所有对话历史"""
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    convs = {}
    for f in CONV_DIR.glob("*.json"):
        try:
            convs[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except:
            pass
    return convs


def save_conversation(session_id: str, data: dict):
    """保存对话历史"""
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    (CONV_DIR / f"{session_id}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ─── 路由 ────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "客服引擎", "version": "1.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """对话入口"""
    from src.intent import classify_intent
    from src.dialog import DialogManager
    from src.rag import search_kb

    config = load_config()
    convs = load_conversations()
    session = convs.get(req.session_id, {"history": [], "turns": 0, "last_intent": None})

    # 意图识别
    intent_result = classify_intent(req.message, config)

    # 知识库检索
    kb_results = []
    if intent_result["intent"] != "unknown":
        kb_results = await search_kb(req.message, k=config.get("kb_top_k", 3))

    # 对话管理 + 回复生成
    dialog = DialogManager(session, config)
    reply, session = dialog.process(req.message, intent_result, kb_results)

    # 保存
    convs[req.session_id] = session
    save_conversation(req.session_id, session)

    return ChatResponse(
        reply=reply,
        intent=intent_result["intent"],
        confidence=intent_result["confidence"],
        session_id=req.session_id,
        turn_count=session["turns"]
    )


@app.post("/intent", response_model=IntentResponse)
async def get_intent(req: IntentRequest):
    """意图识别"""
    from src.intent import classify_intent
    config = load_config()
    result = classify_intent(req.message, config)
    return IntentResponse(**result)


@app.post("/kb/search", response_model=KBSearchResponse)
async def kb_search(req: KBSearchRequest):
    """知识库检索"""
    from src.rag import search_kb
    results = await search_kb(req.query, k=req.top_k)
    return KBSearchResponse(results=results, query=req.query, count=len(results))


@app.get("/kb/list")
async def kb_list():
    """列出知识库文件"""
    files = []
    for f in KNOWLEDGE_DIR.glob("*.md"):
        size = f.stat().st_size
        files.append({"name": f.stem, "file": f.name, "size": size})
    return {"knowledge_base": files, "count": len(files)}


@app.get("/conversations")
async def list_conversations():
    """列出所有对话"""
    convs = load_conversations()
    result = []
    for sid, data in convs.items():
        result.append({
            "session_id": sid,
            "turns": data.get("turns", 0),
            "last_intent": data.get("last_intent", "unknown"),
            "updated": data.get("updated_at", "")
        })
    return {"conversations": result, "count": len(result)}


@app.get("/stats")
async def stats():
    """系统统计"""
    convs = load_conversations()
    total_turns = sum(c.get("turns", 0) for c in convs.values())
    kb_files = list(KNOWLEDGE_DIR.glob("*.md"))

    return {
        "total_sessions": len(convs),
        "total_turns": total_turns,
        "kb_files": len(kb_files),
        "kb_content_chars": sum(f.read_text(encoding="utf-8").__len__() for f in kb_files)
    }
