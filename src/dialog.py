"""
多轮对话状态机
管理 session 上下文，支持多轮对话
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


class DialogManager:
    """多轮对话管理器"""

    def __init__(self, session: dict, config: dict):
        self.session = session
        self.config = config
        self.max_turns = config.get("max_turns", 10)
        self.history_window = config.get("history_window", 6)

    def process(self, user_message: str, intent_result: dict, kb_results: list) -> tuple:
        """
        处理一轮对话
        返回：(reply, updated_session)
        """
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
        reply = self._generate_reply(user_message, intent_result, kb_results)

        # 追加助手回复
        history.append({
            "role": "assistant",
            "message": reply,
            "ts": datetime.now().isoformat()
        })
        self.session["history"] = history

        return reply, self.session

    def _generate_reply(self, message: str, intent: dict, kb_results: list) -> str:
        """根据意图生成回复"""
        intent_type = intent.get("intent", "unknown")

        repliers = {
            "greeting": self._reply_greeting,
            "bye": self._reply_bye,
            "shipping": self._reply_shipping,
            "returns": self._reply_returns,
            "price": self._reply_price,
            "product": self._reply_product,
            "stock": self._reply_stock,
            "complaint": self._reply_complaint,
        }

        replier = repliers.get(intent_type, self._reply_unknown)
        return replier(message, intent, kb_results)

    def _reply_greeting(self, msg: str, intent: dict, kb: list) -> str:
        return "你好！我是智能客服助手，有什么可以帮您的？"

    def _reply_bye(self, msg: str, intent: dict, kb: list) -> str:
        return "感谢您的咨询，祝您生活愉快！有其他问题随时联系我们~"

    def _reply_shipping(self, msg: str, intent: dict, kb: list) -> str:
        # 优先使用知识库内容
        if kb:
            kb_text = kb[0].get("content", "")[:200]
            return f"关于物流问题：{kb_text}...\n\n如需进一步咨询，请提供更详细的订单信息。"
        return "您好！关于物流问题，一般发货后3-5个工作日送达。如需查询具体订单物流，请提供订单号。"

    def _reply_returns(self, msg: str, intent: dict, kb: list) -> str:
        if kb:
            kb_text = kb[0].get("content", "")[:200]
            return f"关于退换货：{kb_text}...\n\n如需办理退货，请通过订单页面申请。"
        return "您好！支持7天无理由退换货（不影响二次销售）。质量问题可享受全额退款。请提供订单号和具体问题描述。"

    def _reply_price(self, msg: str, intent: dict, kb: list) -> str:
        return "您好！目前店铺有满减活动，满199减20，满299减50。具体商品价格请看商品详情页。"

    def _reply_product(self, msg: str, intent: dict, kb: list) -> str:
        if kb:
            kb_text = kb[0].get("content", "")[:200]
            return f"关于商品详情：{kb_text}..."
        return "您好！请问您想了解哪款商品的详情？可以提供商品名称或链接，我帮您查询。"

    def _reply_stock(self, msg: str, intent: dict, kb: list) -> str:
        return "您好！商品库存状态会在页面实时更新。如需确认特定商品库存，请告知商品名称。"

    def _reply_complaint(self, msg: str, intent: dict, kb: list) -> str:
        return "非常抱歉给您带来不好的体验！请您详细描述问题，我们会第一时间为您处理。您也可以拨打客服电话：400-XXX-XXXX。"

    def _reply_unknown(self, msg: str, intent: dict, kb: list) -> str:
        if kb:
            kb_text = kb[0].get("content", "")[:150]
            return f"我理解您的问题。关于这个话题：{kb_text}...\n\n如果这不是您想问的，请重新描述您的问题。"
        return "抱歉，我没有完全理解您的问题。请换个说法，或者告诉我您具体想咨询什么？"
