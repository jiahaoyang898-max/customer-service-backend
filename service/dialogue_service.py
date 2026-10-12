from api.schemas import HistoryMessage
from domain.messages import UserMessage, ProcessResult
from domain.state import DialogueState
from prompts.history_builder import HistoryBuilder
from repository.dialogue_state_repository import DialogueStateRepository
from engine.dialogue_engine import DialogueEngine

class DialogueService:
    """
    处理对话的业务类
    """
    def __init__(self,dialogue_state_repository: DialogueStateRepository,dialogue_engine: DialogueEngine):
        self.dialogue_state_repository = dialogue_state_repository
        self.dialogue_engine = dialogue_engine

    async def process_message(self,user_message: UserMessage) -> ProcessResult:
        """
        核心处理逻辑
        """
        #读取对话内容
        dialogue_state:DialogueState = await self.dialogue_state_repository.load_state(user_message.sender_id)
        #处理最新消息（改state）
        process_result: ProcessResult = await self.dialogue_engine.process_message(dialogue_state,user_message)
        #存储对话内容
        await self.dialogue_state_repository.save_state(dialogue_state)
        #返回本轮处理结果
        return process_result

    async def load_chat_history(self, sender_id: str) -> list[HistoryMessage]:
        # 根据 sender_id 从数据库加载完整 DialogueState(读状态)
        state = await self.dialogue_state_repository.load_state(sender_id)
        # 遍历 state.sessions，把每个 turn 展开成消息列表
        chat_messages : list[HistoryMessage] = []
        for session in state.sessions:
            for turn in session.turns:
                chat_messages.append(HistoryBuilder.render_user_message(session.session_id, turn.user_message))
                chat_messages.extend([HistoryBuilder.render_bot_messages(session.session_id, b_msg) for b_msg in turn.bot_messages])
        return chat_messages






