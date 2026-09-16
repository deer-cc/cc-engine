"""
知识库检索测试
"""
import pytest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import KnowledgeBase, get_kb, search_kb


def test_kb_load():
    """测试知识库加载"""
    kb_dir = Path(__file__).parent.parent / "knowledge"
    kb = KnowledgeBase(kb_dir)
    assert len(kb.chunks) > 0, "知识库应该有内容"
    assert len(kb.inverted_index) > 0, "倒排索引不应该为空"


def test_kb_search():
    """测试知识库搜索"""
    kb_dir = Path(__file__).parent.parent / "knowledge"
    kb = KnowledgeBase(kb_dir)

    results = kb.search("发货时间", top_k=3)
    assert len(results) > 0, "应该能搜到结果"
    assert results[0]["score"] > 0, "得分应该大于0"


def test_kb_search_returns():
    """测试退换货相关搜索"""
    kb_dir = Path(__file__).parent.parent / "knowledge"
    kb = KnowledgeBase(kb_dir)

    results = kb.search("退货", top_k=3)
    assert len(results) > 0, "应该能搜到退换货相关内容"


def test_kb_search_empty():
    """测试空查询"""
    kb_dir = Path(__file__).parent.parent / "knowledge"
    kb = KnowledgeBase(kb_dir)

    results = kb.search("", top_k=3)
    # 空查询可能返回空结果，不强制要求
    assert isinstance(results, list)


def test_kb_chunk_structure():
    """测试 chunk 结构"""
    kb_dir = Path(__file__).parent.parent / "knowledge"
    kb = KnowledgeBase(kb_dir)

    if kb.chunks:
        chunk = kb.chunks[0]
        assert "id" in chunk
        assert "content" in chunk
        assert "source" in chunk
        assert len(chunk["content"]) > 0


def test_sync_search():
    """测试同步搜索"""
    kb_dir = Path(__file__).parent.parent / "knowledge"
    kb = KnowledgeBase(kb_dir)
    results = kb.search("物流", top_k=2)
    assert isinstance(results, list)
    if results:
        assert "content" in results[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
