from models.base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import TEXT

class DialogueStateRecord(Base):
    """
    对话状态记录
    """
    __tablename__ = "dialogue_states"
    sender_id: Mapped[str] = mapped_column(primary_key=True)
    state_json: Mapped[str] = mapped_column(TEXT, nullable=False, default={})