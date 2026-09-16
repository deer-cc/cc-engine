"""
意图识别模块
多级分类策略：LLM 为主 + 关键词兜底
"""
import json
import os
import re
import asyncio
import httpx
from typing import Dict, Any, Optional
from pathlib import Path

# ─── 关键词规则（兜底）────────────────────────────────────
KEYWORD_RULES = {
    "shipping": ["物流", "快递", "发货", "什么时候到", "运费", "包邮", "配送", "驿站", "件"],
    "returns": ["退换", "退货", "退款", "不满意", "质量问题", "换货", "退回", "七天"],
    "price": ["多少钱", "价格", "优惠", "便宜", "打折", "降价", "活动", "券"],
    "product": ["什么材质", "尺寸", "规格", "颜色", "款式", "好不好", "正品", "真假"],
    "stock": ["有货", "库存", "还能买", "缺货", "预售", "补货"],
    "greeting": ["你好", "在吗", "嗨", "在不在", "hello", "hi"],
    "bye": ["再见", "拜拜", "谢谢", "感谢", "晚安"],
    "complaint": ["差评", "投诉", "欺骗", "假货", "骗人", "垃圾", "太差"],
}

# ─── 优先级顺序（关键词兜底时按此顺序匹配）─────────────────
KEYWORD_PRIORITY = ["complaint", "returns", "shipping", "price", "product", "stock", "greeting", "bye"]


def classify_by_keywords(message: str) -> Optional[Dict[str, Any]]:
    """关键词规则匹配（兜底，不依赖 LLM）"""
    msg_lower = message.lower()

    for keyword in KEYWORD_PRIORITY:
        patterns = KEYWORD_RULES.get(keyword, [])
        if any(p in msg_lower for p in patterns):
            # 对 greeting/bye 设置低置信度
            confidence = 0.9 if keyword not in ("greeting", "bye") else 0.7
            return {
                "intent": keyword,
                "confidence": round(confidence, 2),
                "method": "keyword",
                "labels": _extract_labels(message, keyword)
            }

    return None


def _extract_labels(message: str, intent: str) -> Dict:
    """从消息中提取实体标签"""
    labels = {}
    if intent == "returns":
        if "质量问题" in message or "质量" in message:
            labels["return_reason"] = "质量问题"
        elif "不喜欢" in message or "不想要" in message:
            labels["return_reason"] = "主观原因"
    elif intent == "shipping":
        if "运费" in message:
            labels["query_type"] = "运费"
        elif "什么时候" in message:
            labels["query_type"] = "时效"
    return labels


async def classify_by_llm(message: str, config: dict) -> Dict[str, Any]:
    """LLM 意图分类（主路径）"""
    system_prompt = """你是一个客服意图识别器。分析用户消息的意图，输出 JSON：

{
  "intent": "shipping|returns|price|product|stock|greeting|bye|complaint|unknown",
  "confidence": 0.0-1.0,
  "summary": "一句话总结用户意图"
}

意图说明：
- shipping: 物流/快递/发货/运费相关
- returns: 退换/退货/退款/质量问题相关
- price: 价格/优惠/活动相关
- product: 商品详情/材质/尺寸/真假相关
- stock: 库存/有货/预售相关
- greeting: 打招呼/问候
- bye: 告别/感谢
- complaint: 投诉/差评/质疑
- unknown: 无法归类

只输出 JSON，不要其他文字。"""

    messages = [{"role": "user", "content": f"用户消息：{message}"}]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{config['llm_base_url']}/v1/messages",
                headers={
                    "Authorization": f"Bearer {config['llm_api_key']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": config.get("llm_model", "claude-opus-4-8-20251101"),
                    "max_tokens": 200,
                    "system": system_prompt,
                    "messages": messages
                }
            )
            resp.raise_for_status()
            data = resp.json()

            text = ""
            for block in data.get("content", []):
                if isinstance(block, dict) and block.get("type") == "text":
                    text += block.get("text", "")

            result = _parse_llm_response(text)
            result["method"] = "llm"
            return result

    except Exception as e:
        # LLM 失败时降级为关键词匹配
        return {"intent": "unknown", "confidence": 0.0, "method": "error", "error": str(e)}


def _parse_llm_response(text: str) -> Dict[str, Any]:
    """解析 LLM 返回的 JSON"""
    text = text.strip()
    # 提取 JSON
    match = re.search(r"\{[^}]+\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # 降级处理
    return {"intent": "unknown", "confidence": 0.0, "summary": text[:50]}


async def classify_intent(message: str, config: dict) -> Dict[str, Any]:
    """
    意图识别入口：LLM 为主，关键词兜底
    返回：{intent, confidence, method, labels}
    """
    # Step 1: LLM 分类
    llm_result = await classify_by_llm(message, config)

    # Step 2: 如果 LLM 失败或置信度低，用关键词兜底
    if llm_result.get("method") == "error" or llm_result.get("confidence", 0) < 0.5:
        keyword_result = classify_by_keywords(message)
        if keyword_result:
            keyword_result["confidence"] = max(keyword_result["confidence"], llm_result.get("confidence", 0))
            return keyword_result

    return llm_result
