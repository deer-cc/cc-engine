"""查询改写模块：将口语化输入转换为知识库标准术语"""
import re
from typing import List


# ─── 同义词映射表 ──────────────────────────────────────────────
# 策略：口语化表达 → 知识库标准术语（追加到 query 末尾）

SYNONYM_MAP = {
    # 退换货领域
    "坏了": ["质量问题", "有缺陷"],
    "瑕疵": ["质量问题", "有瑕疵"],
    "不满意": ["无理由退货", "七天退换"],
    "不想要": ["无理由退货", "七天退换"],
    "能退吗": ["退换货", "退货政策"],
    "可以退吗": ["退换货", "退货政策"],
    "想退": ["退换货", "退货政策"],
    "怎么退": ["退换货流程", "退货方式"],
    "质量不行": ["质量问题", "有缺陷"],
    "做工差": ["质量问题", "有缺陷"],
    "质量有问题": ["质量问题", "有缺陷"],
    "想换": ["换货", "退换货"],
    "怎么换": ["换货流程", "退换货"],

    # 物流领域
    "多久到货": ["物流时效", "快递时间"],
    "什么时候发": ["发货时间", "发货时效"],
    "啥时候发": ["发货时间", "发货时效"],
    "发了吗": ["物流状态", "发货查询"],
    "到哪了": ["物流状态", "快递位置"],
    "快递单号": ["物流查询", "快递单号"],
    "运费多少": ["运费标准", "包邮规则"],
    "包不包邮": ["运费标准", "包邮规则"],
    "什么时候送到": ["物流时效", "快递时间"],
    "寄到哪里": ["收货地址", "物流查询"],
    "物流太慢": ["物流时效", "快递投诉"],

    # 价格领域
    "便宜点": ["价格优惠", "活动折扣"],
    "有优惠": ["价格优惠", "活动折扣"],
    "打几折": ["价格优惠", "活动折扣"],
    "减多少钱": ["价格优惠", "活动折扣"],
    "有活动": ["价格优惠", "活动折扣"],
    "打折吗": ["价格优惠", "活动折扣"],

    # 商品领域
    "啥材质": ["商品材质", "规格参数"],
    "什么颜色": ["商品颜色", "规格参数"],
    "正品吗": ["商品真伪", "正品保证"],
    "真假": ["商品真伪", "正品保证"],
    "好不好": ["商品评价", "口碑"],

    # 通用
    "在哪": ["商品位置", "店铺地址"],
    "联系谁": ["客服联系方式", "客服电话"],
}

# ─── 近义扩展表 ──────────────────────────────────────────────
# 策略：将近义术语也注入 query，扩大召回范围

NEAR_SYNONYMS = {
    "退货": ["退换货", "退款"],
    "换货": ["退换货", "换商品"],
    "快递": ["物流", "发货"],
    "物流": ["快递", "发货"],
    "发货": ["快递", "物流"],
    "发票": ["电子发票", "发票"],
    "地址": ["收货地址", "地址修改"],
    "退款": ["退货退款", "退款流程"],
}

# ─── 停用词 ──────────────────────────────────────────────
STOP_WORDS = {"的", "了", "是", "在", "我", "你", "他", "她", "它",
              "这", "那", "么", "吧", "吗", "呢", "啊", "哦", "嗯",
              "很", "好", "都", "也", "又", "再", "最", "比", "被", "把",
              "一个", "这个", "那个", "什么", "怎么", "哪里"}


def rewrite_query(query: str) -> str:
    """
    查询改写：口语化输入 → 标准术语扩展

    策略：
    1. 精确同义词追加（扩大召回）
    2. 近义扩展注入（提高匹配率，跳过已在 query 中的标准术语）
    3. 保留原查询（不覆盖原始意图）

    返回：改写后的查询字符串（包含原查询 + 扩展术语）
    """
    if not query or not query.strip():
        return ""

    rewritten = query.strip()

    # 策略1：精确同义词追加
    for colloquial, terms in SYNONYM_MAP.items():
        if colloquial in rewritten:
            for term in terms:
                if term not in rewritten:
                    rewritten += f" {term}"

    # 策略2：近义扩展（跳过已在 query 中的术语，避免冗余）
    expanded_terms = set()
    for key, values in NEAR_SYNONYMS.items():
        if key in rewritten:
            for v in values:
                # 如果标准术语已经出现在 query 中，不再追加
                if v not in rewritten:
                    expanded_terms.add(v)

    if expanded_terms:
        rewritten += " " + " ".join(expanded_terms)

    return rewritten


def extract_keywords_improved(text: str) -> List[str]:
    """
    改进版关键词提取：
    - jieba 分词（整词精度）+ 中文双字滑窗（字面召回兜底）取并集
    - 无 jieba 时纯规则降级

    为什么要并集：jieba 在短问句上会把整句切成单字（"还能买吗"→还/能/买/吗），
    过滤后关键词为空；而长文档里同样的字面组合也可能被切碎而丢掉。
    两者互补：整词保证精度，bigram 保证不会"零召回"。

    返回：去重关键词列表（保持出现顺序）
    """
    keywords: List[str] = []

    # 1) jieba 整词
    try:
        import jieba
        for w in jieba.cut(text):
            w = w.strip()
            if len(w) >= 2 and w not in STOP_WORDS:
                keywords.append(w)
    except ImportError:
        pass

    # 2) 中文双字滑窗（字面召回兜底）
    text_cn = re.sub(r'[^一-龥]', '', text)
    for i in range(len(text_cn) - 1):
        bg = text_cn[i:i + 2]
        if bg not in STOP_WORDS:
            keywords.append(bg)

    # 3) 英文单词
    for word in re.findall(r'[a-zA-Z]{2,}', text):
        keywords.append(word.lower())

    # 4) 无任何关键词时，退回标点分割的长短语（极端兜底）
    if not keywords:
        tokens = re.split(r'[,\s，。！？、：;；\n]+', text)
        keywords = [t.strip() for t in tokens
                    if len(t.strip()) >= 2 and t.strip() not in STOP_WORDS]

    return list(dict.fromkeys(keywords))


def test_rewrite_example():
    """自测用例"""
    cases = [
        ("我买的东西坏了", ["质量问题", "有缺陷"]),
        ("能退吗", ["退换货", "退货政策"]),
        ("什么时候发", ["发货时间", "发货时效"]),
        ("包不包邮", ["运费标准", "包邮规则"]),
    ]
    for query, expected_terms in cases:
        result = rewrite_query(query)
        for term in expected_terms:
            assert term in result, f"改写失败: {query} → {result}, 缺少 {term}"
    print("所有改写测试通过")


if __name__ == "__main__":
    test_rewrite_example()
