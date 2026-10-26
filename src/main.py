from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json
import os
from pathlib import Path
from datetime import datetime

# P3: 顶层导入（消除函数内import代码异味）
from src.intent import classify_intent
from src.dialog import DialogManager
from src.rag import search_kb
from src.confidence import get_confidence_level
from src.request_log import RequestLog

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
    confidence_level: str  # high / medium / low — v1.1 新增
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

# P0优化：config 启动时缓存，避免每次请求读盘
_config_cache: Optional[dict] = None


def load_config() -> dict:
    """加载配置（带模块级缓存）"""
    global _config_cache
    if _config_cache is None:
        if CONFIG_FILE.exists():
            try:
                _config_cache = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except:
                pass
        if _config_cache is None:
            _config_cache = {
                "llm_base_url": os.getenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:15721"),
                "llm_api_key": os.getenv("ANTHROPIC_AUTH_TOKEN", "PROXY_MANAGED"),
                "llm_model": os.getenv("LLM_MODEL", "claude-opus-4-8-20251101"),
                "max_turns": 10,
                "history_window": 6,
                "kb_top_k": 3,
            }
    return _config_cache


def refresh_config() -> dict:
    """强制刷新配置缓存（修改 config.json 后调用）"""
    global _config_cache
    _config_cache = None
    return load_config()


def load_conversation(session_id: str) -> dict:
    """按需加载单个对话会话（P0优化：替代全量加载）"""
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    conv_file = CONV_DIR / f"{session_id}.json"
    if conv_file.exists():
        try:
            return json.loads(conv_file.read_text(encoding="utf-8"))
        except:
            pass
    return {"history": [], "turns": 0, "last_intent": None}


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
    """对话入口（企业增强：全链路日志 + 请求ID + 降级标注）"""
    config = load_config()
    session = load_conversation(req.session_id)

    # 全链路日志开始
    log = RequestLog()
    log.query = req.message
    log.llm_model = config.get("llm_model")

    # 意图识别（P0修复：补await，LLM意图识别才能真正执行）
    intent_result = await classify_intent(req.message, config)
    log.intent = intent_result.get("intent")

    # v1.1: 置信度校准
    confidence_level = get_confidence_level(
        intent_result["confidence"],
        intent_result["intent"]
    )

    # 知识库检索
    kb_results = []
    if intent_result["intent"] != "unknown":
        kb_results = await search_kb(req.message, k=config.get("kb_top_k", 3))
    log.kb_hits = len(kb_results)

    # 对话管理 + 回复生成（降级信息回传给日志）
    dialog = DialogManager(session, config)
    reply, session = await dialog.process(req.message, intent_result, kb_results)

    # 把降级/报错信息写回日志（dialog 生成的降级标记挂在 session 上）
    degrade_info = session.pop("_last_degrade", None)
    if degrade_info:
        log.degraded = True
        log.degrade_reason = degrade_info.get("reason")
        log.error_type = degrade_info.get("error_type")
    # token 用量（dialog 里记录到 session）
    log.input_tokens = session.pop("_llm_input_tokens", None)
    log.output_tokens = session.pop("_llm_output_tokens", None)
    log.close(reply)

    # 保存（直接写入单个 session 文件）
    save_conversation(req.session_id, session)

    return ChatResponse(
        reply=reply,
        intent=intent_result["intent"],
        confidence=intent_result["confidence"],
        confidence_level=confidence_level,
        session_id=req.session_id,
        turn_count=session["turns"]
    )


@app.post("/intent", response_model=IntentResponse)
async def get_intent(req: IntentRequest):
    """意图识别"""
    config = load_config()
    result = await classify_intent(req.message, config)
    # LLM 路径可能不返回 labels 字段, 补默认值避免 500
    result.setdefault("labels", {})
    return IntentResponse(**result)


@app.post("/kb/search", response_model=KBSearchResponse)
async def kb_search(req: KBSearchRequest):
    """知识库检索"""
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
    """列出所有对话（懒加载：只读文件名+元数据）"""
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for f in sorted(CONV_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "session_id": f.stem,
                "turns": data.get("turns", 0),
                "last_intent": data.get("last_intent", "unknown"),
                "updated": data.get("updated_at", "")
            })
        except:
            pass
    return {"conversations": result, "count": len(result)}


@app.get("/stats")
async def stats():
    """系统统计"""
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    conv_files = list(CONV_DIR.glob("*.json"))
    total_sessions = len(conv_files)
    total_turns = 0
    for f in conv_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            total_turns += data.get("turns", 0)
        except:
            pass
    kb_files = list(KNOWLEDGE_DIR.glob("*.md"))

    return {
        "total_sessions": total_sessions,
        "total_turns": total_turns,
        "kb_files": len(kb_files),
        "kb_content_chars": sum(f.read_text(encoding="utf-8").__len__() for f in kb_files)
    }
