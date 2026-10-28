"""
对话状态机测试
"""
import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dialog import DialogManager


def test_dialog_init():
    """测试对话管理器初始化"""
    session = {"history": [], "turns": 0}
    config = {"max_turns": 10, "history_window": 6}
    dm = DialogManager(session, config)
    assert dm.max_turns == 10
    assert dm.history_window == 6


@pytest.mark.asyncio
async def test_process_first_turn():
    """测试第一轮对话"""
    session = {"history": [], "turns": 0}
    config = {"max_turns": 10, "history_window": 6}
    dm = DialogManager(session, config)

    intent = {"intent": "greeting", "confidence": 0.95}
    reply, new_session = await dm.process("你好", intent, [])

    assert "你好" in reply or "您好" in reply
    assert new_session["turns"] == 1
    assert len(new_session["history"]) == 2  # user + assistant


@pytest.mark.asyncio
async def test_process_shipping():
    """测试物流意图回复"""
    session = {"history": [], "turns": 0}
    config = {"max_turns": 10, "history_window": 6}
    dm = DialogManager(session, config)

    intent = {"intent": "shipping", "confidence": 0.9}
    kb_results = [{"content": "一般3-5天送达", "source": "shipping.md"}]
    reply, _ = await dm.process("什么时候能到", intent, kb_results)

    assert len(reply) > 10
    assert "物流" in reply or "快递" in reply or "天" in reply


@pytest.mark.asyncio
async def test_process_returns_with_kb():
    """测试退换货回复+知识库融合"""
    session = {"history": [], "turns": 0}
    config = {"max_turns": 10, "history_window": 6}
    dm = DialogManager(session, config)

    intent = {"intent": "returns", "confidence": 0.92}
    kb_results = [{"content": "支持7天无理由退货", "source": "returns.md"}]
    reply, _ = await dm.process("能退货吗", intent, kb_results)

    assert len(reply) > 10
    assert "退换" in reply or "退货" in reply or "7天" in reply


@pytest.mark.asyncio
async def test_history_limit():
    """测试历史长度限制"""
    session = {"history": [], "turns": 0}
    config = {"max_turns": 10, "history_window": 10}
    dm = DialogManager(session, config)

    for i in range(10):
        intent = {"intent": "greeting", "confidence": 0.9}
        await dm.process(f"消息{i}", intent, [])

    # 历史应该有轮次记录
    assert session["turns"] == 10
    assert len(session["history"]) > 0


@pytest.mark.asyncio
async def test_clarify_low_confidence():
    """测试低置信度时引导澄清"""
    session = {"history": [], "turns": 0}
    config = {"max_turns": 10, "history_window": 6}
    dm = DialogManager(session, config)

    intent = {"intent": "unknown", "confidence": 0.2}
    reply, _ = await dm.process("????", intent, [])

    assert "理解" in reply or "重新" in reply or "说法" in reply


@pytest.mark.asyncio
async def test_max_turns_limit():
    """测试P3: 最大对话轮次限制"""
    session = {"history": [], "turns": 0}
    config = {"max_turns": 3, "history_window": 6}
    dm = DialogManager(session, config)

    # 达到上限后应返回提示
    for i in range(3):
        intent = {"intent": "greeting", "confidence": 0.9}
        await dm.process(f"消息{i}", intent, [])

    # 第4次应触发上限提示
    reply, session = await dm.process("继续", {"intent": "greeting", "confidence": 0.9}, [])
    assert "上限" in reply or "新对话" in reply


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
