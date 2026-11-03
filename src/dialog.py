"""
多轮对话状态机
管理 session 上下文，支持多轮对话
置信度校准：分层阈值 + 澄清策略（v1.1）
v3.0 体验层：回复生成外移到 src/reply_gen.py——自然语言回答、KB 只作依据不吐原文、
模板兜底不编造政策、降级说人话（对标成熟电商客服体验）
企业增强：429/522 分错处理 + 降级原因回传（供全链路日志）
"""
import re
from datetime import datetime

from src.confidence import should_clarify, get_confidence_level, get_clarification_prompt
from src.reply_gen import ReplyGenerator, should_escalate


class DialogManager:
    """多轮对话管理器"""

    def __init__(self, session: dict, config: dict):
        self.session = session
        self.config = config
        self.max_turns = config.get("max_turns", 10)
        self.history_window = config.get("history_window", 6)
        self.gen = ReplyGenerator(session, config)

    async def process(self, user_message: str, intent_result: dict, kb_results: list) -> tuple:
        """
        处理一轮对话（async，避免阻塞事件循环）
        返回：(reply, updated_session)
        """
        # P3: 检查最大对话轮次
        if self.session.get("turns", 0) >= self.max_turns:
            self.session["turns"] = self.session.get("turns", 0) + 1
            self.session["last_intent"] = "max_turns_reached"
            self.session["updated_at"] = datetime.now().isoformat()
            history = self.session.get("history", [])
            history.append({
                "role": "assistant",
                "message": "本次对话轮次较多，为确保回答质量，请开启新对话继续～",
                "ts": datetime.now().isoformat()
            })
            self.session["history"] = history
            return "本次对话轮次较多，为确保回答质量，请开启新对话继续～", self.session

        # 更新轮次
        self.session["turns"] = self.session.get("turns", 0) + 1
        self.session["last_intent"] = intent_result.get("intent", "unknown")
        self.session["updated_at"] = datetime.now().isoformat()

        # 保存历史
        history = self.session.get("history", [])
        history.append({
            "role": "user",
            "message": user_message,
            "intent": intent_result.get("intent"),
            "ts": datetime.now().isoformat()
        })

        # 限制历史长度
        if len(history) > self.history_window * 2:
            history = history[-self.history_window * 2:]
        self.session["history"] = history

        # 根据意图生成回复
        reply = await self._generate_reply(user_message, intent_result, kb_results)

        # 追加助手回复
        history.append({
            "role": "assistant",
            "message": reply,
            "ts": datetime.now().isoformat()
        })
        self.session["history"] = history

        return reply, self.session

    async def _generate_reply(self, message: str, intent: dict, kb_results: list) -> str:
        """根据意图生成回复（v3.0: 回复生成走 reply_gen 体验层；v3.1: 转人工硬规则）"""
        intent_type = intent.get("intent", "unknown")
        confidence = intent.get("confidence", 0.0)

        # v3.1 转人工硬规则：承诺/纠纷/超纲问题一律不硬答，优先于所有其他分支
        # 放在澄清之前——投诉/承诺类问题不该用"换个说法"打发，直接给人工
        if should_escalate(message, intent_type):
            return ("这个问题涉及承诺/售后，我这边不随便给您答复，"
                    "已为您转接人工客服处理，请稍等～")

        # v1.1: 低置信度触发澄清策略
        if should_clarify(confidence, intent_type):
            return get_clarification_prompt(intent_type, confidence)

        # 招呼/告别：直接人话回复，不进 LLM
        if intent_type == "greeting":
            return "您好！我在的，有什么可以帮您的？"
        if intent_type == "bye":
            return "好的，感谢您的咨询！有问题随时来找我～"

        # P3修复: 使用 get_confidence_level() 而非硬编码 0.85
        if get_confidence_level(confidence, intent_type) == "high":
            llm_reply = await self.gen.natural_reply(message, intent_type, kb_results)
            if llm_reply:
                return llm_reply

        # LLM 不可用 → 模板兜底（不再编造政策，见 reply_gen.FALLBACKS）
        return self.gen.fallback_reply(intent_type, kb_results)
