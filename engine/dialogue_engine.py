import time
from typing import Dict

from chitchat.handler import ChitChatHandler
from clarify.responder import ClarifyResponder
from domain import state
from domain.state import DialogueState
from domain.messages import UserMessage, ProcessResult, BotMessage, MessageType, FocusedObject
from knowledge.handler import KnowledgeHandler
from knowledge.intents import KNOWLEDGE_INTENTS
from plan.models import ClarifyReason, KnowledgeTurnPlan
from plan.turn_planner import TurnPlanner
from plan.turn_validator import TurnPlanValidator
from task.command.models import Command, SetSlotsCommand
from task.flow.flows import FlowsList
from task.flow.steps import CollectFlowStep
from task.handler import TaskHandler


class DialogueEngine:
    """
        对话引擎
    """
    def __init__(
            self,
            turn_planner: TurnPlanner,
            task_handler: TaskHandler,
            knowledge_handler: KnowledgeHandler,
            chitchat_handler: ChitChatHandler,
            clarify_responder: ClarifyResponder,
            turn_plan_validator: TurnPlanValidator,
    ) -> None:
        self.turn_planner = turn_planner
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler
        self.clarify_responder = clarify_responder
        self.turn_plan_validator = turn_plan_validator

    async def process_message(self,dialogue_state:DialogueState,user_message:UserMessage) -> ProcessResult:
        self._prepare_session(dialogue_state)
        self._begin_turn(dialogue_state, user_message)
        if user_message.type is MessageType.TEXT:
            #按消息类型分流
            messages = await self._handle_text_message(dialogue_state)

        else:
            dialogue_state.set_focused_object(user_message.object)
            messages = await self._handle_object_message(message=user_message, state=dialogue_state)
        #把本轮回复写入turn
        dialogue_state.pending_turn.bot_messages.extend(messages)
        #提交:turn 进入 session 历史
        dialogue_state.commit_turn()
        #返回组装结果
        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=messages,
        )

    def _prepare_session(self, dialogue_state:DialogueState) -> None:
        """
        准备会话
        """
        session = dialogue_state.current_session()
        if session is None:
            dialogue_state.start_session()
            return
        now = time.time()
        if now - session.last_activity_at > 60*60:
            dialogue_state.close_current_session()
            dialogue_state.reset_runtime_state_for_new_session()
            dialogue_state.start_session()
        else:
            session.last_activity_at = now

    def _begin_turn(self, dialogue_state:DialogueState, user_message:UserMessage) -> None:
        """
        开始一个turn
        """
        dialogue_state.begin_turn(user_message)

    async def _handle_text_message(self, dialogue_state:DialogueState) -> list[BotMessage]:
        turn_plan = await self.turn_planner.predict(dialogue_state, self.task_handler.flows)
        validation = self.turn_plan_validator.validate(
            state=dialogue_state,
            turn_plan=turn_plan,
            flow_list=self.task_handler.flows,  # 注意：你 validator 的形参名叫 flow_list
            intents=KNOWLEDGE_INTENTS,
        )
        if not validation.valid:
            return await self.clarify_responder.respond(
                state=dialogue_state, reason=validation.reason,
            )
        #按轨道分发
        if turn_plan.task is  not None:
            return await self.task_handler.handle(
                commands=turn_plan.task.commands,
                state = dialogue_state,
            )
        elif turn_plan.knowledge is not None:
            # 3.2 信息检索
            return await self.knowledge_handler.handle(intents=turn_plan.knowledge.intents, state=dialogue_state)
        else:
            # 3.3 闲聊
            return await self.chitchat_handler.handle(state=dialogue_state)

    async def _handle_object_message(
            self,
            message:UserMessage,
            state:DialogueState,
    )->list[BotMessage]:
        commands = self._resolve_object_commands(
            message = message,
            state = state,
            flows = self.task_handler.flows,
        )
        if commands:
            # 场景 A:对象能填当前槽 → 转成命令,推进流程
            return await self.task_handler.handle(commands=commands,state=state)
        # 没有匹配到 slot。如果用户正在一个流程中,不打断,让流程继续
        if state.active_task is not None:
            # 场景 C:在流程里但槽不匹配 → 不打断,空命令让流程继续
            return await self.task_handler.handle(commands=[], state=state)
        #场景 B:没有流程 → 澄清
        return await self.clarify_responder.respond(
            state=state,
            reason=ClarifyReason.OBJECT_REQUIRES_INTENT,
        )

    def _resolve_object_commands(
            self,
            message: UserMessage,
            state: DialogueState,
            flows: FlowsList,
    ) -> list[Command]:
        message_object = message.object
        if message_object is None:
            return []
        object_type = message_object.type.strip().lower()
        if object_type == "order":
            if self._flow_has_unfilled_collect_slot(state, flows, "order_number"):
                return [SetSlotsCommand(
                    command="set_slots",
                    slots={"order_number": message_object.id},
                )]
            return []
        if object_type == "product":
            if self._flow_has_unfilled_collect_slot(state, flows, "product_id"):
                return [SetSlotsCommand(
                    command="set_slots",
                    slots={"product_id": message_object.id},
                )]
            return []
        return []

    #能否填槽的判断
    @staticmethod
    def _flow_has_unfilled_collect_slot(
            state: DialogueState,
            flows: FlowsList,
            slot_name:str,
    )->bool:
        active_task = state.active_task
        if active_task is None:
            return False
        flow = flows.get_flow_by_id(active_task.flow_id)
        if flow is None:
            return False
        if active_task.slots.get(slot_name):
            return False
        for step in flow.steps:
            if isinstance(step,CollectFlowStep) and step.slot_name == slot_name:
                return True
        return False













