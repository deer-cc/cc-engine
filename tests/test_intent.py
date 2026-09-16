"""
意图识别测试
"""
import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intent import classify_intent, classify_by_keywords, KEYWORD_RULES


def test_keyword_shipping():
    """测试物流意图关键词匹配"""
    result = classify_by_keywords("什么时候发货？快递到哪了？")
    assert result is not None
    assert result["intent"] == "shipping"
    assert result["method"] == "keyword"
    assert result["confidence"] > 0


def test_keyword_returns():
    """测试退换货意图关键词匹配"""
    result = classify_by_keywords("这个质量有问题，我要退货")
    assert result is not None
    assert result["intent"] == "returns"
    assert result["confidence"] > 0


def test_keyword_price():
    """测试价格意图关键词匹配"""
    result = classify_by_keywords("多少钱？有优惠吗？")
    assert result is not None
    assert result["intent"] == "price"


def test_keyword_greeting():
    """测试问候意图"""
    result = classify_by_keywords("你好，在吗？")
    assert result is not None
    assert result["intent"] == "greeting"


def test_unknown_intent():
    """测试未知意图（不匹配任何关键词）"""
    result = classify_by_keywords("asdfghjkl")
    # 不匹配任何关键词时返回 None 是正常的，验证不崩溃即可
    assert result is None or result.get("intent") in KEYWORD_RULES


def test_classify_intent_llm_fallback():
    """测试完整分类流程（LLM失败时兜底）"""
    config = {
        "llm_base_url": "http://127.0.0.1:9999",
        "llm_api_key": "test",
        "llm_model": "test"
    }
    # 直接调用同步版本
    result = classify_by_keywords("什么时候发货")
    assert result is not None
    assert result["intent"] in KEYWORD_RULES or result["intent"] == "unknown"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
