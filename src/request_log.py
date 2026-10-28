"""
全链路请求日志模块（企业增强层）
记录: 请求ID / 提问 / 检索片段数 / 模型token / 耗时 / 报错类型(401/429/500/522)
落盘: D:\\AI软件\\核心引擎\\客服引擎\\request_logs\\YYYY-MM-DD.jsonl (每行一条JSON)

设计要点:
- 只记"结构字段"不记完整原文(提问截断到200字), 控制日志膨胀
- 凭证零明文: 只记 error_type 分类, 不记 API key
- 线程/协程安全: 用 append + 加锁, 避免并发写坏文件
"""
import json
import threading
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

LOG_DIR = Path(__file__).parent.parent / "request_logs"

_lock = threading.Lock()


class RequestLog:
    """一次请求的日志上下文, 在 /chat 入口创建, 各阶段往里填字段"""

    def __init__(self):
        self.request_id = uuid.uuid4().hex[:12]
        self.start_ts = datetime.now().isoformat()
        self.duration_ms: Optional[int] = None
        self.query: Optional[str] = None
        self.intent: Optional[str] = None
        self.kb_hits: int = 0
        self.degraded: bool = False
        self.degrade_reason: Optional[str] = None  # 为何降级(如 llm_429_fallback)
        self.error_type: Optional[str] = None      # 401/429/403/500/522/timeout/none
        self.llm_model: Optional[str] = None
        self.input_tokens: Optional[int] = None
        self.output_tokens: Optional[int] = None
        self.assistant_reply_len: Optional[int] = None

    def close(self, assistant_reply: Optional[str] = None):
        """请求结束时调用, 填充耗时并落盘"""
        if assistant_reply is not None:
            self.assistant_reply_len = len(assistant_reply)
        end = datetime.now()
        self.duration_ms = int((end - datetime.fromisoformat(self.start_ts)).total_seconds() * 1000)
        self._write()

    def _write(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        day = datetime.now().strftime("%Y-%m-%d")
        record = {
            "request_id": self.request_id,
            "ts": self.start_ts,
            "duration_ms": self.duration_ms,
            "query": (self.query or "")[:200],
            "intent": self.intent,
            "kb_hits": self.kb_hits,
            "degraded": self.degraded,
            "degrade_reason": self.degrade_reason,
            "error_type": self.error_type or "none",
            "llm_model": self.llm_model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "assistant_reply_len": self.assistant_reply_len,
        }
        with _lock:
            try:
                with open(LOG_DIR / f"{day}.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except OSError as e:
                # 日志写失败（Windows 下杀毒/索引服务可能瞬时锁文件）
                # 绝不能因为日志问题让整个请求 500 —— 降级为 stderr 提示
                import sys
                print(f"[request_log] 写盘失败，已跳过本条日志: {e}", file=sys.stderr)


def classify_error(exc: Exception) -> str:
    """把异常归类成 error_type, 便于统计'哪类错最多'。
    只判类型不记凭证/原文。"""
    msg = str(exc).lower()
    code = getattr(exc, "status_code", None)
    if code in (401, 403):
        return "401" if code == 401 else "403"
    if code == 429 or "rate" in msg or "限流" in msg or "quota" in msg:
        return "429"
    if code in (500, 502, 503, 504):
        return "522" if code in (502, 503, 504) else "500"
    if "timeout" in msg or "timed out" in msg:
        return "timeout"
    if code is not None:
        return str(code)
    return "other"
