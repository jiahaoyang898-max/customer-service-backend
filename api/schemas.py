from pydantic import BaseModel, model_validator


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

    @model_validator(mode="after")
    def _check_message_payload(self) -> "ChatRequest":
        """
        text 与 object 至少要有一个非空，否则请求非法。
        校验失败交给 FastAPI 返回 422，避免下游按 OBJECT 处理 None 对象导致 500。
        """
        has_text = self.text is not None and self.text.strip() != ""
        if not has_text and self.object is None:
            raise ValueError("text 和 object 不能同时为空：请至少提供一条文本消息或一个聚焦对象")
        return self

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







