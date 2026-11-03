"""
回复生成模块（v3.0 体验层）

对标成熟电商客服（言犀/小蜜级别）的体验标准：
1. 回答是自然语言，不吐知识库原文（旧版把 FAQ 原文"Q12: ..."倒给买家）
2. KB 片段只作为 LLM 依据，不直接回显；来源以一句话备注
3. LLM 不可用时降级模板不再编造政策（旧版写死"满199减20/400-XXX"）
4. 降级话术说人话，不暴露"模型限流/基础应答"等系统细节
5. v3.1 转人工硬规则：承诺类/纠纷类/超纲类问题一律不硬答，明确转人工
   （对标文档"AI客服最怕的是乱回复，宁慢勿错"的核心主张）
"""
import json
import re
from typing import Dict, Any, List, Optional

import httpx

# 知识库片段里残留的题库编号（Q1/Q12:）清洗
_QA_MARKERS = re.compile(r'^Q\d+[\.:：]', re.M)


# ─── 转人工硬规则（v3.1 验收修正版）────────────────────────
# 原则：AI 客服最怕"乱回复"。涉及承诺、纠纷、超纲的问题，一律不硬答，转人工。
# 这三类是文档博主点名的"AI 永远填不了"的坑——宁可慢一点、转给人工，也不说错话。
#
# 叶子验收修正（2026-11-02）：
# 1. 移除"赠品/便宜点/优惠点"——它们是价格/促销类，KB 答得上（query_rewriter 有映射），
#    划进转人工会误杀正常问询（demo 第 5 问"有赠品吗"本该展示"拒答"却被转人工抢走）。
# 2. "一定/保证"等高频子串改为整词匹配，避免"不一定""有质量保证"被误杀。
ESCALATE_PATTERNS: List[str] = [
    # 承诺类：涉及价格承诺、时效承诺、特殊承诺，答错就要赔
    "承诺", "包退", "包换", "赔付", "赔偿", "肯定能",
    "发票", "开票", "开专票", "增值税发票",
    "包价", "打折给我", "送东西",
    # 纠纷类：投诉/差评/假货质疑，必须人工介入，AI 硬答容易激化
    "投诉", "差评", "骗人", "欺骗", "假货", "欺诈", "举报", "消费者协会",
    "12315", "曝光",
    # 超纲类：超出电商客服常规范围（法律/医疗/个性化定制）
    "律师", "法院", "起诉", "维权",
    "过敏", "药物", "药用",
]
# 高频子串需整词匹配（防止"不一定/有质量保证"被裸 in 误杀）
_ESCALATE_WHOLE_WORDS: List[str] = ["保证", "一定"]
_ESCALATE_WHOLE_RE = re.compile(
    r'(?<![不有会要能可])(' + '|'.join(re.escape(w) for w in _ESCALATE_WHOLE_WORDS) + r')(?![的质])'
)


def should_escalate(message: str, intent: str) -> bool:
    """判断是否需要转人工（承诺/纠纷/超纲命中任一关键词，或投诉意图高置信）"""
    # 投诉意图本身就该转人工，不看关键词
    if intent == "complaint":
        return True
    # 普通关键词：裸子串匹配（这些词单独出现即高风险）
    if any(p in message for p in ESCALATE_PATTERNS):
        return True
    # 高频子串：整词匹配，排除"不/有/会"等否定或常规语境
    if _ESCALATE_WHOLE_RE.search(message):
        return True
    return False


def clean_kb_text(chunks: List[Dict], single_block: bool = False) -> str:
    """把检索到的 KB 片段拼成 LLM 可直接引用的素材。
    清洗题库编号与 markdown 标记，保留原始事实，去掉格式噪音。

    single_block=True 时只取第一个"单段、可直接说出口"的片段，
    多行/多段/带表格的跳过——避免 fallback 拼出乱码给人看。"""
    parts: List[str] = []
    for r in (chunks or [])[:3]:
        raw = (r.get("content") or "").strip()
        if not raw:
            continue
        raw = _QA_MARKERS.sub('', raw)
        text = re.sub(r'[*_`#]+', '', raw)
        # KB 片段里混着 markdown 表格/多行编号时，自然语言拼接会很乱——
        # 单段模式下直接跳过这种片段
        if '\n' in raw and single_block:
            continue
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) >= 10:
            parts.append(text[:300])
            if single_block:
                break
    return "\n".join(parts)


class ReplyGenerator:
    """把 意图 + KB 检索结果 变成可交付给买家/用户看的自然语言回复"""

    _SOURCES: Dict[str, str] = {}  # 首次回答后缓存，避免同一会话重复说"来自FAQ"

    def __init__(self, session: Dict, config: Dict):
        self.session = session
        self.config = config

    async def natural_reply(self, message: str, intent: str, kb_results: List[Dict]) -> Optional[str]:
        """让 LLM 依据 KB 片段生成 1-3 句自然语言回答。

        成功返回回答文本；LLM 不可用/回答不合格返回 None（调用方走模板兜底）。
        降级原因回写到 session["_last_degrade"]，与旧行为一致，供全链路日志。
        """
        kb_context = clean_kb_text(kb_results)

        sources = "、".join(
            dict.fromkeys((r.get("source") or "").strip().lstrip("（(").rstrip("）)")
                          for r in kb_results[:3] if r.get("source"))
        ) if kb_results else "知识库"

        source_note = f"（以上信息来自{sources}）"

        system_prompt = (
            "你是一家网店的智能客服，正在回答买家消息。要求：\n"
            "1. 只依据「知识库参考」作答，参考没有的内容一律不编造；确实没有就说"
            "『这块我这边暂时没有相关资料，您方便的话我帮您转人工确认』，不要瞎猜。\n"
            "2. 口吻像真人客服：简洁（2-3句）、直接给结论，不要复述问题，不要输出"
            "「知识库参考」「Q12」之类的内部结构，也不要逐条念参考原文。\n"
            "3. 用户问「这个/这件」等指代时按通用政策回答。\n"
            f"4. 回答末尾用一句自然话备注来源：{source_note}\n"
        )
        user_content = f"买家问：{message}\n\n知识库参考：\n{kb_context}" if kb_context \
            else f"买家问：{message}\n\n知识库参考：（未检索到相关资料）"

        try:
            import asyncio
            resp = await self._llm_call(system_prompt, user_content)
            if resp:
                usage = resp.pop("_usage", None) or {}
                if usage and self.session is not None:
                    self.session["_llm_input_tokens"] = usage.get("input_tokens")
                    self.session["_llm_output_tokens"] = usage.get("output_tokens")
                text = self._extract_text(resp)
                # 防复读：LLM 偶发回显提示词时丢弃
                if text and "知识库参考" not in text and len(text) > 8:
                    return text
            return None

        except httpx.HTTPStatusError as e:
            from src.request_log import classify_error
            etype = classify_error(e)
            self.session["_last_degrade"] = {
                "reason": f"llm_{etype}_fallback",
                "error_type": etype,
            }
            return None
        except httpx.TimeoutException:
            self.session["_last_degrade"] = {"reason": "llm_timeout_fallback", "error_type": "timeout"}
            return None
        except Exception:
            self.session["_last_degrade"] = {"reason": "llm_error_fallback", "error_type": "other"}
            return None

    async def _llm_call(self, system_prompt: str, user_content: str,
                         max_tokens: int = 250, temperature: float = 0.3) -> Optional[dict]:
        import asyncio
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await asyncio.wait_for(client.post(
                f"{self.config['llm_base_url']}/v1/messages",
                headers={
                    "Authorization": f"Bearer {self.config.get('llm_api_key', '')}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config.get("llm_model", "claude-opus-4-8-20251101"),
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_content}]
                }
            ), timeout=10)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _extract_text(data: dict) -> Optional[str]:
        text = ""
        for block in data.get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                text += block.get("text", "")
        return text.strip() or None

    # ─── 模板兜底（LLM 不可用）─────────────────────────────────
    # 原则：没有 KB 依据就不给具体数字/政策，宁可用"我帮您转人工确认"

    FALLBACKS: Dict[str, str] = {
        "shipping": "您好，关于物流这块我这边暂时没有查到确切的资料，不给您瞎说——我帮您转人工客服确认一下，可以吗？",
        "returns": "退换货的具体政策我这边暂时没有查到完整资料，为了不给您错误信息，我帮您转人工确认一下好吗？",
        "price": "价格和优惠活动我这边暂时没有查到准确信息，不随便报数，我帮您转人工客服确认一下。",
        "product": "商品详情我这边暂时没有查到对应资料，您方便的话告诉我具体是哪款，我帮您问一下。",
        "stock": "库存状态我这边暂时没有查到，我帮您确认一下再回复您，好吗？",
        "complaint": "非常抱歉给您带来不好的体验！您方便把具体情况（订单号/遇到的问题）发我吗，我马上帮您转人工优先处理。",
        "unknown": "抱歉，这个问题我这边暂时没有相关资料，不能瞎答——您换个说法我再试试，或者我帮您转人工确认？",
    }

    def fallback_reply(self, intent: str, kb_results: List[Dict]) -> str:
        """LLM 不可用时的兜底回复。
        KB 有「单段、可直接说出口」的内容时回显该段；
        多行/多段/带表格的片段不硬拼（会乱），走拒答话术。"""
        kb_text = clean_kb_text(kb_results, single_block=True)
        base = self.FALLBACKS.get(intent, self.FALLBACKS["unknown"])
        if kb_text:
            return f"{kb_text}（资料里能看到的内容如上，更详细的我帮您转人工确认）"
        return base

    async def resolve_reference(self, message: str, history: List[Dict]) -> str:
        """上下文指代消解（v3.1）：
        买家分段发消息、用"这个/几久/洗了褪色"等指代时，
        结合最近几轮 history 把指代补全成可独立检索的完整问句。
        返回补全后的 query（LLM 不可用时原样返回，不阻塞检索）。"""
        if not history or len(message) < 2:
            return message
        # 没有明显指代词/短口语时，不用调 LLM（省成本）
        if not re.search(r'[这那它他她个]|\b[几多啥哪]\w|褪色|掉色|不想要|还能', message):
            return message
        # 取最近 3 轮做上下文
        recent = [
            f"{t.get('role')}：{t.get('message','')[:40]}"
            for t in history[-6:]
        ]
        try:
            import asyncio
            resp = await self._llm_call(
                "你是电商客服的上下文理解助手。根据对话历史，把买家最新一句里的指代词（这个/那个/几久等）补全成一句可独立检索的完整问句。只输出补全后的问句，不要解释。若无需补全则原样输出。",
                f"对话历史：\n" + "\n".join(recent) + f"\n\n买家最新一句：{message}\n\n补全后："
            )
            if resp:
                text = self._extract_text(resp)
                if text and len(text) <= 40:
                    return text
        except Exception:
            pass
        return message
