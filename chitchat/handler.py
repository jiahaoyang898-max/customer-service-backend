from domain.messages import BotMessage
from domain.state import DialogueState
from chitchat.responder import ChitChatResponder

class ChitChatHandler:
    """
    聊天处理程序
    """
    def __init__(self, responder: ChitChatResponder):
        self.responder = responder

    async def handle(self,state:DialogueState)->list[BotMessage]:
        #当前待处理轮次
        pending_turn = state.pending_turn
        #当前用户消息
        user_message = pending_turn.user_message
        #最近对话历史
        recent_turns = state.current_session().turns
        return await self.responder.respond(
            user_message=user_message,
            recent_turns=recent_turns,
        )