"""置信度校准测试"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.confidence import (
    get_confidence_level, should_clarify, get_clarification_prompt,
    CONFIDENCE_THRESHOLDS, INTENT_HIGH_THRESHOLD_OVERRIDES
)


class TestConfidenceLevel:
    """置信度层级判定测试"""

    def test_high_confidence(self):
        """高置信度判定"""
        assert get_confidence_level(0.95, "shipping") == "high"
        assert get_confidence_level(0.90, "greeting") == "high"
        assert get_confidence_level(0.85, "unknown") == "high"

    def test_medium_confidence(self):
        """中置信度判定"""
        assert get_confidence_level(0.75, "shipping") == "medium"
        assert get_confidence_level(0.65, "returns") == "medium"
        assert get_confidence_level(0.60, "price") == "medium"

    def test_low_confidence(self):
        """低置信度判定"""
        assert get_confidence_level(0.40, "shipping") == "low"
        assert get_confidence_level(0.30, "unknown") == "low"
        assert get_confidence_level(0.0, "complaint") == "low"

    def test_boundary_high(self):
        """边界值：恰好等于 high 阈值"""
        assert get_confidence_level(0.85, "unknown") == "high"

    def test_boundary_medium(self):
        """边界值：恰好等于 medium 阈值"""
        assert get_confidence_level(0.60, "unknown") == "medium"


class TestIntentOverrides:
    """意图专属阈值覆盖测试"""

    def test_complaint_high_threshold(self):
        """投诉意图需要更高置信度才能判定为 high"""
        # complaint 专属 high 阈值 0.75，medium 仍为 0.60
        assert get_confidence_level(0.70, "complaint") == "medium"  # 0.60-0.75 → medium
        assert get_confidence_level(0.75, "complaint") == "high"    # >= 0.75 → high
        assert get_confidence_level(0.80, "complaint") == "high"    # >= 0.75 → high
        # 低于 medium 阈值 → low
        assert get_confidence_level(0.50, "complaint") == "low"

    def test_default_high_threshold(self):
        """默认意图使用 0.85 作为 high 阈值"""
        assert get_confidence_level(0.80, "shipping") == "medium"   # 低于 0.85
        assert get_confidence_level(0.85, "shipping") == "high"     # 等于 0.85
        assert get_confidence_level(0.90, "shipping") == "high"     # 高于 0.85

    def test_unknown_default(self):
        """未知意图使用默认阈值"""
        assert get_confidence_level(0.80, "unknown") == "medium"    # 低于 0.85
        assert get_confidence_level(0.90, "unknown") == "high"      # 高于 0.85


class TestShouldClarify:
    """澄清触发判定测试"""

    def test_should_not_clarify_high(self):
        """高置信度不触发澄清"""
        assert should_clarify(0.90, "shipping") == False
        assert should_clarify(0.85, "unknown") == False

    def test_should_not_clarify_medium(self):
        """中置信度不触发澄清"""
        assert should_clarify(0.70, "returns") == False
        assert should_clarify(0.60, "price") == False

    def test_should_clarify_low(self):
        """低置信度触发澄清"""
        assert should_clarify(0.40, "shipping") == True
        assert should_clarify(0.30, "unknown") == True
        assert should_clarify(0.0, "complaint") == True


class TestClarificationPrompts:
    """澄清提示生成测试"""

    def test_shipping_prompt(self):
        """物流意图澄清提示"""
        prompt = get_clarification_prompt("shipping", 0.3)
        assert "物流" in prompt or "快递" in prompt or "运费" in prompt

    def test_returns_prompt(self):
        """退换货意图澄清提示"""
        prompt = get_clarification_prompt("returns", 0.3)
        assert "退货" in prompt or "换货" in prompt or "质量" in prompt

    def test_price_prompt(self):
        """价格意图澄清提示"""
        prompt = get_clarification_prompt("price", 0.3)
        assert "价格" in prompt or "优惠" in prompt or "活动" in prompt

    def test_product_prompt(self):
        """商品意图澄清提示"""
        prompt = get_clarification_prompt("product", 0.3)
        assert "材质" in prompt or "尺寸" in prompt

    def test_unknown_prompt(self):
        """未知意图澄清提示"""
        prompt = get_clarification_prompt("unknown", 0.2)
        assert "理解" in prompt or "重新" in prompt or "说法" in prompt

    def test_stock_prompt(self):
        """库存意图澄清提示"""
        prompt = get_clarification_prompt("stock", 0.3)
        assert "库存" in prompt or "预售" in prompt


class TestConfigValidity:
    """配置合理性检查"""

    def test_threshold_ordering(self):
        """阈值顺序正确"""
        assert CONFIDENCE_THRESHOLDS["high"] > CONFIDENCE_THRESHOLDS["medium"]
        assert CONFIDENCE_THRESHOLDS["medium"] > CONFIDENCE_THRESHOLDS["low"]

    def test_all_intents_have_overrides(self):
        """所有意图都有合理的覆盖阈值"""
        intents = ["shipping", "returns", "price", "product", "stock",
                   "greeting", "bye", "complaint", "unknown"]
        for intent in intents:
            level = get_confidence_level(0.5, intent)
            assert level in ("high", "medium", "low"), f"Intent {intent} returned invalid level"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
