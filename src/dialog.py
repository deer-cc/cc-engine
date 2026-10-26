"""
多轮对话状态机
管理 session 上下文，支持多轮对话
置信度校准：分层阈值 + 澄清策略（v1.1）
LLM回复生成：高置信度时生成个性化回复（v2.0）
企业增强：429/522 分错处理 + 降级原因回传（供全链路日志）
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

import httpx
from src.confidence import should_clarify, get_confidence_level, get_clarification_prompt
from src.request_log import classify_error


class DialogManager:
    """多轮对话管理器"""

    def __init__(self, session: dict, config: dict):
        self.session = session
        self.config = config
        self.max_turns = config.get("max_turns", 10)
        self.history_window = config.get("history_window", 6)

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
                "message": "对话轮次已达上限，请开启新对话。",
                "ts": datetime.now().isoformat()
            })
            self.session["history"] = history
            return "对话轮次已达上限，请开启新对话。", self.session

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
        """根据意图生成回复（v2.0: 高置信度时使用LLM生成个性化回复）"""
        intent_type = intent.get("intent", "unknown")
        confidence = intent.get("confidence", 0.0)

        # v1.1: 低置信度触发澄清策略
        if should_clarify(confidence, intent_type):
            return get_clarification_prompt(intent_type, confidence)

        # v2.0: 高置信度时尝试LLM生成个性化回复
        # P3修复: 使用 get_confidence_level() 而非硬编码 0.85
        if get_confidence_level(confidence, intent_type) == "high":
            llm_reply = await self._generate_llm_reply(message, intent_type, kb_results)
            if llm_reply and llm_reply != intent_type:
                return llm_reply

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

    async def _generate_llm_reply(self, message: str, intent: str, kb_results: list) -> Optional[str]:
        """高置信度时用LLM生成个性化回复（async，不阻塞事件循环）。
        企业增强：429 限流不再静默降级——记录降级原因+报错类型到 session，供全链路日志统计。"""
        try:
            kb_context = ""
            if kb_results:
                kb_context = "\n".join(r.get("content", "")[:300] for r in kb_results[:2])

            system_prompt = """你是一个专业且友好的电商客服助手。根据知识库内容回答用户问题，要求：
1. 回答简洁准确，直接解决用户问题
2. 如果知识库没有相关信息，礼貌地说明并建议联系客服
3. 使用温暖亲切的语气
4. 不要编造知识库里没有的信息"""

            user_content = f"用户问：{message}\n\n知识库参考：{kb_context}"

            async with httpx.AsyncClient(timeout=8) as client:
                resp = await asyncio.wait_for(client.post(
                    f"{self.config['llm_base_url']}/v1/messages",
                    headers={
                        "Authorization": f"Bearer {self.config['llm_api_key']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.config.get("llm_model", "claude-opus-4-8-20251101"),
                        "max_tokens": 300,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_content}]
                    }
                ), timeout=8)
                resp.raise_for_status()
                data = resp.json()

                # 记录 token 用量（供成本统计，企业增强层要项）
                usage = data.get("usage", {})
                if self.session is not None:
                    self.session["_llm_input_tokens"] = usage.get("input_tokens")
                    self.session["_llm_output_tokens"] = usage.get("output_tokens")

                text = ""
                for block in data.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        text += block.get("text", "")

                text = text.strip()
                # 验证不是空回复或错误信息
                if text and len(text) > 5 and text != intent:
                    return text
                return None

        except httpx.HTTPStatusError as e:
            # 企业增强：分错处理——429 限流 / 5xx 网关 / 4xx 鉴权, 归类记录后降级
            etype = classify_error(e)
            self.session["_last_degrade"] = {
                "reason": f"llm_{etype}_fallback",
                "error_type": etype,
            }
            # 429 特别处理: 友好降级话术(提示稍后再试), 不反复重试(避免雪崩)
            if etype == "429":
                return "（系统繁忙：模型服务当前限流，已为您切换到基础应答。请稍后重试您的问题~）"
            return None
        except asyncio.TimeoutError:
            self.session["_last_degrade"] = {"reason": "llm_timeout_fallback", "error_type": "timeout"}
            return None
        except Exception:
            # 其它未知错误: 静默降级到模板回复(原有行为)
            self.session["_last_degrade"] = {"reason": "llm_error_fallback", "error_type": "other"}
            return None

    def _reply_greeting(self, msg: str, intent: dict, kb: list) -> str:
        return "你好！我是智能客服助手，有什么可以帮您的？"

    def _reply_bye(self, msg: str, intent: dict, kb: list) -> str:
        return "感谢您的咨询，祝您生活愉快！有其他问题随时联系我们~"

    def _reply_shipping(self, msg: str, intent: dict, kb: list) -> str:
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
