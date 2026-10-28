"""
知识库检索模块
双路召回：关键词匹配 + TF-IDF 向量相似度
查询改写：口语化输入 → 标准术语扩展
TTL缓存：相同query在30s内直接返回缓存结果
"""
import re
import json
import math
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from src.query_rewriter import rewrite_query, extract_keywords_improved


# P2优化：检索结果缓存，相同query在TTL内直接返回
_kb_cache: Dict[str, tuple] = {}
KB_CACHE_TTL = 30  # 秒


class KnowledgeBase:
    """本地知识库（Markdown 文件）"""

    def __init__(self, knowledge_dir: Path):
        self.kb_dir = knowledge_dir
        self.chunks: List[Dict] = []
        self.inverted_index: Dict[str, List[int]] = {}
        self.tf_idf: Dict[int, Dict[str, float]] = {}
        self._load()

    def _load(self):
        """加载所有知识库文件并构建索引"""
        self.chunks = []
        self.inverted_index = {}
        self.tf_idf = {}

        if not self.kb_dir.exists():
            return

        chunk_id = 0
        for md_file in self.kb_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                chunks = self._split_chunks(content, source=str(md_file.name))
                self.chunks.extend(chunks)
                # 构建倒排索引和 TF-IDF
                for i, chunk in enumerate(chunks):
                    cid = len(self.chunks) - len(chunks) + i
                    self._build_index(cid, chunk)
            except Exception as e:
                print(f"[KB] 加载 {md_file.name} 失败: {e}")

    def _split_chunks(self, content: str, source: str, chunk_size: int = 300) -> List[Dict]:
        """将 Markdown 内容分割为 chunk"""
        chunks = []
        paragraphs = content.split("\n\n")
        current_chunk = ""
        current_title = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 检测标题
            if para.startswith("#"):
                if current_chunk:
                    chunks.append({
                        "id": len(chunks),
                        "content": current_chunk,
                        "source": source,
                        "title": current_title,
                        "keywords": self._extract_keywords_v2(current_chunk)  # P1: 统一使用改进版
                    })
                current_title = para.replace("#", "").strip()
                current_chunk = para
            else:
                current_chunk += "\n" + para

            # 按 chunk_size 分割长段落
            if len(current_chunk) > chunk_size:
                chunks.append({
                    "id": len(chunks),
                    "content": current_chunk[:chunk_size],
                    "source": source,
                    "title": current_title,
                    "keywords": self._extract_keywords_v2(current_chunk[:chunk_size])  # P1: 统一使用改进版
                })
                current_chunk = current_chunk[chunk_size:]

        if current_chunk.strip():
            chunks.append({
                "id": len(chunks),
                "content": current_chunk,
                "source": source,
                "title": current_title,
                "keywords": self._extract_keywords_v2(current_chunk)  # P1: 统一使用改进版
            })

        return chunks

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（双字滑窗 + 英文单词）— v1.0 基础版，保留用于兼容"""
        keywords = set()
        # 中文双字滑窗
        text_cn = re.sub(r'[^一-龥]', '', text)
        for i in range(len(text_cn) - 1):
            keywords.add(text_cn[i:i+2])
        # 英文单词
        for word in re.findall(r'[a-zA-Z]+', text):
            if len(word) >= 2:
                keywords.add(word.lower())
        return list(keywords)

    def _extract_keywords_v2(self, text: str) -> List[str]:
        """提取关键词（改进版 v1.1）— 使用 query_rewriter 的改进逻辑"""
        return extract_keywords_improved(text)

    def _build_index(self, chunk_id: int, chunk: Dict):
        """构建倒排索引和 TF-IDF"""
        keywords = chunk.get("keywords", [])
        for kw in keywords:
            if kw not in self.inverted_index:
                self.inverted_index[kw] = []
            self.inverted_index[kw].append(chunk_id)

        # TF-IDF
        if chunk_id not in self.tf_idf:
            self.tf_idf[chunk_id] = {}
        for kw in keywords:
            tf = keywords.count(kw) / max(len(keywords), 1)
            df = len(self.inverted_index.get(kw, []))
            idf = math.log(len(self.chunks) / max(df, 1) + 1)
            self.tf_idf[chunk_id][kw] = tf * idf

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """混合检索：查询改写 + 关键词匹配 + TF-IDF 向量相似度（v1.1）"""
        # Step 1: 查询改写（口语化 → 标准术语）
        rewritten_query = rewrite_query(query)

        # Step 2: 关键词提取（使用改进版）
        query_keywords = self._extract_keywords_v2(rewritten_query)

        # 召回候选 chunks
        candidate_ids = set()
        for kw in query_keywords:
            candidate_ids.update(self.inverted_index.get(kw, []))

        if not candidate_ids:
            return []

        # 计算每个 chunk 的得分
        scores = {}
        for cid in candidate_ids:
            # 关键词匹配分
            kw_score = sum(1 for kw in query_keywords if kw in self.tf_idf.get(cid, {}))
            # TF-IDF 向量相似度（简化版：点积）
            vec_score = sum(
                self.tf_idf[cid].get(kw, 0) for kw in query_keywords
            )
            # 融合评分
            scores[cid] = kw_score * 0.5 + vec_score * 0.5

        # 排序取 top_k
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]

        results = []
        for cid in sorted_ids:
            chunk = self.chunks[cid]
            results.append({
                "id": cid,
                "content": chunk["content"],
                "source": chunk["source"],
                "title": chunk["title"],
                "score": round(scores[cid], 4),
                "keywords": chunk.get("keywords", [])
            })

        return results


# 全局知识库实例
_kb_instance = None


def get_kb(knowledge_dir: Path = None) -> KnowledgeBase:
    """获取或创建知识库单例"""
    global _kb_instance
    if _kb_instance is None:
        kb_dir = knowledge_dir or Path(__file__).parent.parent / "knowledge"
        _kb_instance = KnowledgeBase(kb_dir)
    return _kb_instance


async def search_kb(query: str, k: int = 3) -> List[Dict]:
    """异步搜索知识库（带TTL缓存+过期清理）"""
    # P3: 清理过期条目（防止内存泄漏）
    now = time.time()
    expired_keys = [k for k, (v, t) in _kb_cache.items() if now - t >= KB_CACHE_TTL]
    for k in expired_keys:
        del _kb_cache[k]

    # P2: 检查缓存
    cache_key = f"{query}:{k}"
    if cache_key in _kb_cache:
        results, cached_at = _kb_cache[cache_key]
        return results

    # 未命中缓存，执行检索
    kb = get_kb()
    results = kb.search(query, top_k=k)

    # 写入缓存
    _kb_cache[cache_key] = (results, now)
    return results


async def refresh_kb(knowledge_dir: Path = None):
    """重新加载知识库并清空缓存"""
    global _kb_instance
    kb_dir = knowledge_dir or Path(__file__).parent.parent / "knowledge"
    _kb_instance = KnowledgeBase(kb_dir)
    # P2: 清空检索缓存
    _kb_cache.clear()
    return {"status": "ok", "chunks": len(_kb_instance.chunks)}
