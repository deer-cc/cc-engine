"""置信度校准模块：分层阈值 + 澄清策略"""

# ─── 分层阈值配置 ──────────────────────────────────────────────
CONFIDENCE_THRESHOLDS = {
    "high": 0.85,      # 直接回复
    "medium": 0.60,    # 回复但附加提示
    "low": 0.00,       # 触发澄清
}

# ─── 意图专属高阈值覆盖 ──────────────────────────────────────────
# 部分意图需要更高的置信度才能判定为 "high"
# 值表示：该意图的 high 阈值（medium/low 阈值不变）
INTENT_HIGH_THRESHOLD_OVERRIDES = {
    "complaint": 0.75,  # 投诉需要更高置信度才判定为 high
    # 默认 high 阈值：0.85（CONFIDENCE_THRESHOLDS["high"]）
}


def get_confidence_level(confidence: float, intent: str = "unknown") -> str:
    """
    获取置信度层级

    Returns: "high" | "medium" | "low"

    逻辑：
    - 检查该意图是否有专属 high 阈值覆盖
    - 有覆盖：用专属阈值判断 high，否则走标准 medium/low
    - 无覆盖：使用标准三层阈值
    """
    # 检查意图专属 high 阈值
    custom_high = INTENT_HIGH_THRESHOLD_OVERRIDES.get(intent)
    high_threshold = custom_high if custom_high is not None else CONFIDENCE_THRESHOLDS["high"]

    if confidence >= high_threshold:
        return "high"
    elif confidence >= CONFIDENCE_THRESHOLDS["medium"]:
        return "medium"
    else:
        return "low"


def should_clarify(confidence: float, intent: str = "unknown") -> bool:
    """判断是否需要触发澄清策略"""
    return get_confidence_level(confidence, intent) == "low"


def get_clarification_prompt(intent: str, confidence: float) -> str:
    """
    生成澄清提示

    根据意图和置信度生成不同的澄清话术
    """
    prompts = {
        "shipping": "请问您想咨询的是物流时效、快递查询还是运费问题？",
        "returns": "请问您是咨询退货政策、质量问题还是换货流程？",
        "price": "请问您想了解价格、优惠活动还是优惠券？",
        "product": "请问您想了解材质、尺寸还是其他商品信息？",
        "stock": "请问您想查询库存还是预售信息？",
        "unknown": "我没太理解您的问题，能换个说法重新描述一下吗？",
    }
    return prompts.get(intent, prompts["unknown"])
