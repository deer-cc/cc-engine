"""全链路日志 + 429/522 降级处理 的测试（企业增强层）"""
import pytest
import httpx
from src.request_log import RequestLog, classify_error


# ─── classify_error 分错测试 ───

class _FakeHTTP(httpx.HTTPStatusError):
    def __init__(self, code, msg=""):
        super().__init__(msg, request=httpx.Request("POST", "http://x"),
                         response=httpx.Response(code))
        self.status_code = code


@pytest.mark.parametrize("code,expected", [
    (401, "401"), (403, "403"), (429, "429"),
    (500, "500"), (502, "522"), (503, "522"), (504, "522"),
])
def test_classify_error_codes(code, expected):
    assert classify_error(_FakeHTTP(code)) == expected


def test_classify_error_timeout():
    assert classify_error(Exception("Read timed out")) == "timeout"


def test_classify_error_other():
    assert classify_error(Exception("some weird error")) == "other"


# ─── RequestLog 落盘测试 ───

def test_request_log_writes(tmp_path, monkeypatch):
    import src.request_log as rl
    monkeypatch.setattr(rl, "LOG_DIR", tmp_path)
    log = RequestLog()
    log.query = "发货要多久"
    log.intent = "shipping"
    log.kb_hits = 3
    log.close("回复内容")
    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    line = files[0].read_text(encoding="utf-8").splitlines()[-1]
    import json
    rec = json.loads(line)
    assert rec["query"] == "发货要多久"
    assert rec["intent"] == "shipping"
    assert rec["kb_hits"] == 3
    assert rec["assistant_reply_len"] == 4
    assert rec["error_type"] == "none"


def test_request_log_degraded_fields(tmp_path, monkeypatch):
    import src.request_log as rl
    monkeypatch.setattr(rl, "LOG_DIR", tmp_path)
    log = RequestLog()
    log.query = "x"
    log.degraded = True
    log.degrade_reason = "llm_429_fallback"
    log.error_type = "429"
    log.close()
    import json
    rec = json.loads(tmp_path.glob("*.jsonl").__next__().read_text(encoding="utf-8").splitlines()[-1])
    assert rec["degraded"] is True
    assert rec["degrade_reason"] == "llm_429_fallback"
    assert rec["error_type"] == "429"
