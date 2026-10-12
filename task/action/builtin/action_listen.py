import asyncio
from typing import Any

from domain.state import DialogueState
from task.action.base import Action, ActionResult
from task.action.runner import ActionRunner


class ActionListen(Action):
    """
    等待用户输入（信息标记）
    """
    name = "action_listen"
    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        print("action_listen")
        return ActionResult()

if __name__ == "__main__":
    action = ActionListen()
    asyncio.run(action.run(None, None))

