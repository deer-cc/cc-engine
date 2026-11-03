"""
语义检索层（v3.1）
双路召回的第二路：sentence-transformers 本地小模型 embedding + 余弦相似度。

设计要点：
- 与现有 TF-IDF 字面召回**并行**，不替换——字面没召回时用语义兜底
- 本地 CPU 推理，零成本，不依赖 15721 那条 LLM 通道
- 知识库全量 embedding 只做一次，缓存到模块级；KB 刷新（数量变化）自动失效重算
- 模型缺失/推理失败时静默降级：返回空结果，上层走原有 TF-IDF 路径，引擎不崩

零成本约束：默认模型 bge-small-zh-v1.5（~100MB，首次运行自动下载权重）。
可用 EMB_MODEL 环境变量覆盖。
"""
import os
import time
import threading
from typing import List, Dict, Optional
from pathlib import Path

# ─── 模型配置 ───────────────────────────────────────────────
DEFAULT_MODEL = os.getenv("EMB_MODEL", "BAAI/bge-small-zh-v1.5")
# 语义召回与字面召回的合并：语义分 < 此阈值的片段不混入结果（防误召回）
SEMANTIC_MIN_SCORE = float(os.getenv("EMB_MIN_SCORE", "0.35"))

_model: Optional[object] = None
_model_loaded: bool = False
_model_path: Optional[str] = None
_load_lock = threading.Lock()

# ─── 知识库 embedding 缓存（v3.1 性能优化）─────────────────
# key: 知识库指纹（chunk 数 + 首/尾 chunk id），value: (内容哈希, 向量矩阵)
# 命中缓存时只算 query 向量 + 一次矩阵乘法，跳过全量 encode，砍掉大头耗时。
_kb_emb_cache: Dict[str, tuple] = {}


def _kb_fingerprint(chunks: List[Dict]) -> str:
    """知识库指纹：内容任一变化（增删改）都返回不同 key，触发重算"""
    # 用 chunk 数 + 每个 chunk 的 (id, content 哈希前 8) 拼指纹，比"只看数量"更准
    parts = [str(len(chunks))]
    for c in chunks:
        parts.append(f"{c.get('id')}:{hash(c.get('content','')):x}")
    return "|".join(parts)


def _get_or_compute_kb_embeddings(chunks: List[Dict]) -> Optional[object]:
    """取知识库全量向量矩阵，命中缓存直接返回，未命中算一次并缓存"""
    global _kb_emb_cache
    fp = _kb_fingerprint(chunks)
    cached = _kb_emb_cache.get(fp)
    if cached is not None:
        return cached[0]

    model = _load_model()
    if model is None or not chunks:
        return None

    contents = [
        f"{c.get('title','')}\n{c.get('content','')}"[:500]
        for c in chunks
    ]
    matrix = model.encode(contents, normalize_embeddings=True)
    # 限制缓存规模：最多保留 4 个指纹（知识库改动频繁时防无限增长）
    if len(_kb_emb_cache) > 4:
        _kb_emb_cache.pop(next(iter(_kb_emb_cache)))
    _kb_emb_cache[fp] = (matrix, contents)
    return matrix


def _load_model():
    """加载 embedding 模型（线程安全，只加载一次）"""
    global _model, _model_loaded, _model_path
    with _load_lock:
        if _model_loaded:
            return _model
        try:
            from sentence_transformers import SentenceTransformer
            # 本机网络受限（走 proxy，连不上 huggingface.co），
            # 强制离线模式：只从 ~/.cache/huggingface 读已下载权重，不联网校验。
            import os
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            _model = SentenceTransformer(DEFAULT_MODEL)
            _model_path = DEFAULT_MODEL
            _model_loaded = True
            print(f"[emb] 语义检索模型已加载: {DEFAULT_MODEL}")
            return _model
        except Exception as e:
            print(f"[emb] 模型加载失败，语义层降级禁用: {e}")
            _model_loaded = True  # 标记已尝试，避免反复下载
            return None


def semantic_search(
    query: str,
    chunks: List[Dict],
    top_k: int = 3,
    min_score: float = SEMANTIC_MIN_SCORE,
) -> List[Dict]:
    """对知识库全量 chunk 算余弦相似度，返回 top_k 语义相关片段。

    性能：知识库向量矩阵缓存复用，每次只算 query 向量 + 一次点积。
    失败（模型没加载成功）时返回空列表，调用方自然回退到字面路径。
    """
    global _model_loaded, _model
    if not chunks:
        return []

    # 模型没加载过 → 首次同步加载一次（100MB 小模型，几秒可接受）
    # 之后走缓存路径；加载失败才静默降级
    if not _model_loaded:
        _load_model()
        if _model is None:
            return []

    model = _model
    if model is None:
        return []

    t0 = time.perf_counter()
    try:
        kb_matrix = _get_or_compute_kb_embeddings(chunks)
        if kb_matrix is None:
            return []
        emb_query = model.encode([query], normalize_embeddings=True)[0]

        # 余弦相似度（已归一化 → 点积即余弦）
        scores = kb_matrix @ emb_query  # shape: (n_chunks,)

        ranked = sorted(
            range(len(chunks)), key=lambda i: -float(scores[i])
        )[:top_k * 2]  # 多取一倍，按阈值筛

        results = []
        for i in ranked:
            s = float(scores[i])
            if s < min_score:
                continue
            c = chunks[i]
            results.append({
                "id": c["id"],
                "content": c["content"],
                "source": c["source"],
                "title": c.get("title", ""),
                "score": round(s, 4),
                "keywords": c.get("keywords", []),
            })
        return results
    except Exception as e:
        print(f"[emb] 语义检索失败，降级禁用: {e}")
        return []


def _bg_load_model():
    """后台线程首次加载模型（不阻塞请求）"""
    global _model, _model_loaded
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(DEFAULT_MODEL)
        print(f"[emb] 后台加载完成: {DEFAULT_MODEL}")
    except Exception as e:
        print(f"[emb] 后台加载失败: {e}")
    finally:
        _model_loaded = True


def refresh_cache():
    """知识库刷新后清 embedding 缓存（配合 /kb/refresh 调用）"""
    global _kb_emb_cache
    _kb_emb_cache = {}
