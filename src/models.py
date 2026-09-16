"""
数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class IntentResult(BaseModel):
    """意图识别结果"""
    intent: str = Field(..., description="意图类型")
    confidence: float = Field(..., description="置信度 0-1")
    method: str = Field(..., description="识别方式：llm/keyword/error")
    labels: Dict[str, Any] = Field(default_factory=dict, description="实体标签")
    summary: Optional[str] = None


class ConversationTurn(BaseModel):
    """对话轮次"""
    role: str = Field(..., description="user|assistant")
    message: str = Field(..., description="消息内容")
    intent: Optional[str] = None
    ts: str = Field(..., description="时间戳")


class ConversationSession(BaseModel):
    """对话会话"""
    session_id: str
    history: List[ConversationTurn] = Field(default_factory=list)
    turns: int = 0
    last_intent: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息", min_length=1, max_length=500)
    session_id: str = Field("default", description="会话ID")
    stream: bool = Field(False, description="是否流式输出")


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str = Field(..., description="助手回复")
    intent: str = Field(..., description="识别的意图")
    confidence: float = Field(..., description="置信度")
    session_id: str = Field(..., description="会话ID")
    turn_count: int = Field(..., description="当前轮次")


class KBResult(BaseModel):
    """知识库检索结果"""
    id: int = Field(..., description="chunk ID")
    content: str = Field(..., description="内容")
    source: str = Field(..., description="来源文件")
    title: str = Field(..., description="标题")
    score: float = Field(..., description="相关度得分")
    keywords: List[str] = Field(default_factory=list)
