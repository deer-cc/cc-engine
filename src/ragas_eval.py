"""
客服引擎 RAGAS 评估模块 — Phase B v2
检索质量：Recall@K / MRR / 锚点精确率（标注测试集 + 真实检索）
意图质量：准确率（独立评估，不与检索混用）

用法:
  python -m src.ragas_eval
"""
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.rag import get_kb
from src.intent import classify_intent

# ─── 标注测试集 ───────────────────────────────────────────────
# 锚点用 source + anchor（语义子串，匹配 title 或 content），
# 不用整数 doc_id（chunk 切分顺序/标题会随加载变化，不稳定）。
# expected 为 None = 知识库无对应内容，计入分母，命中即失败。
# intent_expected 需与 intent.py 的 KEYWORD_RULES 对齐（无对应意图则留空）。

EVAL_SET_PATH = Path(__file__).parent.parent / "tests" / "eval_set.json"


def load_eval_set() -> List[Dict]:
    return json.loads(EVAL_SET_PATH.read_text(encoding="utf-8"))


def _matches(chunk: Dict, expected: Dict) -> bool:
    """命中判定：source 匹配，且 anchor 出现在 chunk 的 title 或 content 里"""
    if expected is None:
        return False
    if chunk.get("source") != expected.get("source"):
        return False
    anchor = expected.get("anchor", "")
    if not anchor:
        return True
    hay = (chunk.get("title") or "") + "\n" + (chunk.get("content") or "")
    return anchor in hay


def evaluate_retrieval(query: str, expected: Optional[Dict], top_k: int = 3) -> Dict:
    """同步检索评估（直接调 KB，避免 async 缓存/TTL 干扰复现）"""
    kb = get_kb()
    results = kb.search(query, top_k=top_k)

    hit = _matches_any(results, expected)
    # 精确排名：期望锚点第一次出现在第几位
    rank = next((i + 1 for i, r in enumerate(results) if _matches(r, expected)), None)
    # 语义命中但锚点没对上（检索有结果、排序待调优）
    semantic_hit = len(results) > 0 and not hit
    return {
        "query": query,
        "expected": expected,
        "hit": hit,
        "rank": rank,
        "semantic_hit": semantic_hit,
        "results_count": len(results),
    }


def _matches_any(results: List[Dict], expected: Optional[Dict]) -> bool:
    return any(_matches(r, expected) for r in results)


async def evaluate_intent(query: str, expected_intent: str) -> Dict:
    config = _load_minimal_config()
    result = await classify_intent(query, config)
    return {
        "query": query,
        "predicted": result["intent"],
        "expected": expected_intent,
        "confidence": result.get("confidence"),
        "correct": result["intent"] == expected_intent,
    }


def _load_minimal_config() -> dict:
    import os
    return {
        "llm_base_url": os.getenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:15721"),
        "llm_api_key": os.getenv("ANTHROPIC_AUTH_TOKEN", "PROXY_MANAGED"),
        "llm_model": os.getenv("LLM_MODEL", "claude-opus-4-8"),
    }


async def run_full_eval(top_k: int = 3) -> Dict:
    eval_set = load_eval_set()

    # ── 检索评估 ──
    retrieval_results = []
    for item in eval_set:
        try:
            retrieval_results.append(
                evaluate_retrieval(item["query"], item.get("expected"), top_k))
        except Exception as e:
            retrieval_results.append({"query": item["query"],
                                      "expected": item.get("expected"),
                                      "hit": False, "rank": None, "semantic_hit": False,
                                      "results_count": 0, "error": str(e)})

    total = len(retrieval_results)
    hits = sum(1 for r in retrieval_results if r["hit"])
    recall_at_k = hits / max(total, 1)
    semantic_hits = sum(1 for r in retrieval_results if r["semantic_hit"])
    ranks = [r["rank"] for r in retrieval_results if r["rank"] is not None]
    mrr = (sum(1.0 / rk for rk in ranks) / total) if total else 0.0

    # ── 意图评估（独立集）──
    intent_results = []
    for item in eval_set:
        exp = item.get("intent_expected")
        if exp:
            intent_results.append(await evaluate_intent(item["query"], exp))
    intent_acc = (sum(1 for i in intent_results if i["correct"]) /
                  max(len(intent_results), 1))

    return {
        "eval_set": EVAL_SET_PATH.name,
        "retrieval": retrieval_results,
        "intent": intent_results,
        "summary": {
            "total_queries": total,
            "recall_at_k": round(recall_at_k, 4),
            "mrr": round(mrr, 4),
            "semantic_hit_rate": round(semantic_hits / max(total, 1), 4),
            "intent_accuracy": round(intent_acc, 4),
            "retrieval_quality": ("优秀" if recall_at_k >= 0.8
                                  else "良好" if recall_at_k >= 0.6
                                  else "需改进"),
            "intent_quality": ("优秀" if intent_acc >= 0.9
                               else "良好" if intent_acc >= 0.7
                               else "需改进"),
        },
    }


if __name__ == "__main__":
    results = asyncio.run(run_full_eval())
    s = results["summary"]
    print("=" * 60)
    print("客服引擎 RAG 评估报告 (Phase B, v2)")
    print("=" * 60)
    print(f"\n评估集: {s['total_queries']} 条 (tests/eval_set.json)")
    print(f"Recall@3: {s['recall_at_k']:.2%}  |  MRR: {s['mrr']:.3f}  |  语义命中率: {s['semantic_hit_rate']:.2%}")
    print(f"意图准确率: {s['intent_accuracy']:.2%}")
    print(f"检索质量: {s['retrieval_quality']}  |  意图质量: {s['intent_quality']}\n")

    for r in results["retrieval"]:
        mark = "✅" if r["hit"] else ("◐" if r["semantic_hit"] else "❌")
        exp = f"{r['expected']['source']}:{r['expected'].get('anchor','')}" if r["expected"] else "无期望"
        rank_str = f"rank={r['rank']}" if r["rank"] else ("no-hit" if not r["hit"] else "-")
        print(f"  {mark} {r['query']}  → {exp}  ({rank_str}, {r['results_count']}条)")
    print()
    for i in results["intent"]:
        mark = "✅" if i["correct"] else "❌"
        conf = f" conf={i['confidence']}" if i["confidence"] is not None else ""
        print(f"  {mark} {i['query']}  意图: {i['predicted']} (期望 {i['expected']}){conf}")

    report_path = Path(__file__).parent.parent / "ragas_eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n报告已保存: {report_path}")
