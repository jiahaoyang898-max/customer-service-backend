from pydantic import BaseModel


class ChatObject(BaseModel):
    """
    聚焦对象
    """
    type:str
    id: str
    title: str | None=None
    attributes: dict = {}

class ChatRequest(BaseModel):
    """
    请求对象（用户问题）
    """
    sender_id:str
    message_id: str |None = None
    text: str |None = None
    object: ChatObject |None = None

class ChatBotMessage(BaseModel):
    """
    机器人消息
    """
    text: str |None = None
    object: ChatObject |None = None

class ChatResponse(BaseModel):
    """
    响应对象（机器人回复）
    """
    sender_id: str
    message_id: str
    messages: list[ChatBotMessage]

class HistoryMessage(BaseModel):
    """
    历史消息
    """
    session_id: str
    role: str  # user or bot
    text: str | None = None
    object: ChatObject | None = None

class HistoryResponse(BaseModel):
    """
    历史消息列表
    """
    sender_id:str
    messages:list[HistoryMessage]







