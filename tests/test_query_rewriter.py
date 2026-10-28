"""查询改写测试"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.query_rewriter import rewrite_query, extract_keywords_improved, STOP_WORDS


class TestRewriteQuery:
    """查询改写功能测试"""

    def test_rewrite_colloquial_returns(self):
        """测试口语化退换货查询改写"""
        result = rewrite_query("我买的东西坏了")
        assert "质量问题" in result
        assert "有缺陷" in result

    def test_rewrite_colloquial_returns_2(self):
        """测试退换货改写变体"""
        result = rewrite_query("能退吗")
        assert "退换货" in result
        assert "退货政策" in result

    def test_rewrite_colloquial_shipping(self):
        """测试口语化物流查询改写"""
        result = rewrite_query("什么时候发")
        assert "发货时间" in result
        assert "发货时效" in result

    def test_rewrite_colloquial_shipping_2(self):
        """测试物流改写变体"""
        result = rewrite_query("到哪了")
        assert "物流状态" in result
        assert "快递位置" in result

    def test_rewrite_colloquial_price(self):
        """测试价格改写"""
        result = rewrite_query("包不包邮")
        assert "运费标准" in result
        assert "包邮规则" in result

    def test_rewrite_preserves_original(self):
        """测试改写后保留原查询"""
        original = "我买的东西坏了"
        result = rewrite_query(original)
        assert original in result

    def test_rewrite_no_duplication(self):
        """测试改写不重复添加已有术语"""
        query = "质量问题退货"
        result = rewrite_query(query)
        assert result.count("质量问题") == 1
        assert result.count("退货") == 1

    def test_rewrite_already_has_term(self):
        """测试已有标准术语时不重复添加"""
        query = "质量问题退货"
        result = rewrite_query(query)
        # 质量问题已在查询中，不应重复追加
        assert result.count("质量问题") == 1

    def test_empty_query(self):
        """测试空查询"""
        assert rewrite_query("") == ""
        assert rewrite_query("   ") == ""


class TestExtractKeywords:
    """关键词提取功能测试"""

    def test_basic_extraction(self):
        """基础关键词提取"""
        keywords = extract_keywords_improved("商品有质量问题")
        # 降级路径下可能合并为长串，用包含检查
        combined = " ".join(keywords)
        assert "商品" in combined or "质量" in combined

    def test_stopword_filtering(self):
        """停用词过滤"""
        keywords = extract_keywords_improved("这是什么商品")
        assert "的" not in keywords
        assert "什么" not in keywords

    def test_single_char_filtered(self):
        """单字词过滤"""
        keywords = extract_keywords_improved("好吗")
        assert "好" not in keywords

    def test_long_phrase_extraction(self):
        """长句提取"""
        keywords = extract_keywords_improved("七天无理由退货政策支持")
        # 超长短语会被拆分为双字组合
        combined = " ".join(keywords)
        assert "七天" in combined or "退货" in combined or "支持" in combined


class TestIntegration:
    """集成测试：改写 + 关键词提取"""

    def test_rewrite_then_extract(self):
        """改写后关键词提取质量提升"""
        from src.rag import KnowledgeBase
        from pathlib import Path

        kb_dir = Path(__file__).parent.parent / "knowledge"
        kb = KnowledgeBase(kb_dir)

        # 口语化输入改写后搜索
        rewritten = rewrite_query("我买的东西坏了")
        keywords = extract_keywords_improved(rewritten)

        assert len(keywords) > 0
        # 改写后应包含标准术语
        assert any("质量" in kw for kw in keywords) or any("退货" in kw for kw in keywords)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
