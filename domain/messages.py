from enum import Enum
from pydantic import BaseModel

class FocusedObject(BaseModel):
    """
    聚焦对象
    """
    id:str
    type:str
    title:str | None = None
    attributes:dict = {}

class MessageType(Enum):
    TEXT = "text"
    OBJECT = "object"

class UserMessage(BaseModel):
    sender_id: str
    message_id:str
    type:MessageType
    text:str | None = None
    object:FocusedObject | None = None

class BotMessage(BaseModel):
    text:str | None = None
    object:FocusedObject | None = None

class ProcessResult(BaseModel):
    """
    处理结果
    """
    sender_id: str
    message_id: str
    messages: list[BotMessage]

if __name__ == "__main__":
    fo = FocusedObject(id="1",type="2")
    data = fo.model_dump(mode='json')
    obj = FocusedObject.model_validate(data)
    print(type(fo))
    print(type(obj))
    print(type(data))