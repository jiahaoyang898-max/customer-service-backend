import uuid
import time
from pydantic import BaseModel, Field
from typing import Any

from openai import BaseModel
from yaml import CFullLoader

from domain.contexts import TaskContext, SystemContext
from domain.messages import UserMessage, BotMessage, FocusedObject


class Turn(BaseModel):
    """
    本轮对话的对象
    """
    turn_id: str
    user_message:UserMessage
    bot_messages:list[BotMessage]

class Session(BaseModel):
     """
     会话消息
     """
     session_id: str
     started_at:float
     last_activity_at:float
     closed_at:float | None = None
     turns: list[Turn] = []
     paused_tasks: list[Turn] = Field(default_factory=list)

class DialogueState(BaseModel):
    """
    对话状态聚合根
    """
    sender_id : str
    active_task : TaskContext | None = None
    paused_tasks : list[TaskContext] = []
    active_system_task :SystemContext | None = None
    focused_object : FocusedObject | None = None
    sessions : list[Session] = []
    current_session_id : str | None = None
    pending_turn : Turn | None = None

    # 与任务相关

    def start_active_task(self, active_task: TaskContext):
        """
        开始业务任务
        """
        self.active_task = active_task

    def end_active_task(self):
        """
        结束业务任务
        """
        self.active_task = None

    def cancel_active_task(self):
        """
        取消业务任务
        """
        self.active_task = None
        self.active_system_task = None

    def interrupted_active_task(self):
        """
        中断活跃任务
        """
        self.paused_tasks.append(self.active_task)
        self.active_task = None

    def resumed_active_task(self, flow_id: str | None):
        """
        恢复业务任务
        """
        # 1. 判断栈中是否存在中断的业务任务
        if not self.paused_tasks:
            return False
        # 2. 如果业务流程ID不存在
        if flow_id is None:
            self.active_task = self.paused_tasks.pop()
            return True
        # 3. 如果业务流程ID存在
        for i,paused_task in enumerate(self.paused_tasks):
            if paused_task.flow_id == flow_id:
                # 激活
                self.active_task = paused_task
                #删除
                del self.paused_tasks[i]
                return True
        return False


    def start_active_system_task(self, active_system_task: SystemContext):
        """
        开启系统流程
        """
        self.active_system_task = active_system_task

    def end_active_system_task(self):
        """
        结束系统流程
        """
        self.active_system_task = None

    def current_active_task(self):
        """
        返回当前正在执行的任务(系统流程、业务任务)
        """
        return self.active_system_task or self.active_task

    # 与槽位相关
    def set_slots(self, slots: dict[str, Any]):
        """
        设置槽位
        """
        self.active_task.slots.update(slots)

    def remove_slot(self, slot_name: str):
        """
        移除槽位
        """
        self.active_task.slots.remove(slot_name)

    # 与session相关
    def current_session(self) -> Session | None:
        """
        获取当前会话对象
        """
        for session in self.sessions:
            if session.session_id == self.current_session_id:
                return session
        return None

    def start_session(self):
        """
        开启新会话
        """
        if self.current_session() is None:
            now = time.time()
            session_id = str(uuid.uuid4())
            session = Session(
                session_id=session_id,
                started_at=now,
                last_activity_at=now,
            )
            self.sessions.append(session)
            self.current_session_id = session_id

    def close_current_session(self):
        """
        关闭当前会话
        """
        if self.current_session() is not None:
            self.current_session().closed_at = time.time()
            self.current_session_id = None

    def reset_runtime_state_for_new_session(self):
        """
        重置会话状态
        """
        self.active_task = None
        self.active_system_task = None
        self.paused_tasks = []
        self.focused_object = None
        self.pending_turn = None
        self.current_session_id = None

    # 与 turn 相关
    def begin_turn(self, message: UserMessage):
        """
        开始一个turn
        """
        if self.current_session():
            self.pending_turn = Turn(
                turn_id=str(uuid.uuid4()),
                user_message=message,
                bot_messages=[],
            )

    def commit_turn(self):
        """
        提交一个turn
        """
        if self.current_session():
            self.current_session().turns.append(self.pending_turn)
            self.pending_turn = None

    # 与聚焦对象相关
    def set_focused_object(self, focused_object: FocusedObject):
        """
        设置聚焦对象
        """
        self.focused_object = focused_object



