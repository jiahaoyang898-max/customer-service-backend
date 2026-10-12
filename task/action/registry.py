from task.action.base import Action

#行动注册表
class ActionRegistry:
    def __init__(self) -> None:
        self._actions:dict[str,Action] = {}

    def register(self,action:Action) -> None:
        #注册Action，把action存入字典
        self._actions[action.name] = action

    def get(self,name:str) -> Action:
        #根据名字取出对应的Action对象，找不到抛异常
        if name not in self._actions:
            raise KeyError(f"Unknown action '{name}'.")
        return self._actions[name]