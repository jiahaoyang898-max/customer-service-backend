from enum import Enum
from typing import List, Dict, Any, Literal, Annotated
from pydantic import BaseModel, Field, TypeAdapter, field_validator
from task.flow.links import FlowStepLink, StaticLink, ConditionalLink, FallbackLink

class ResponseDefinition(BaseModel):
    """
    响应的模式:静态
    """
    model:str = "static"
    text:str
    prompt:str | None = None

class FlowStepType(Enum):
    """
    流程的步骤类型
    """
    START = "start"
    END = "end"
    ACTION = "action"
    COLLECT = "collect"

class FlowStep(BaseModel):
    """
    流程的步骤 模版
    """
    id:str
    type:FlowStepType
    next:List[FlowStepLink] = []
    description : str = ""

    @classmethod
    def from_dict(cls, step_data:dict[str, Any]) -> "FlowStep":
        """
        多态分发
        """
        step_type = step_data["type"]
        clz = STEP_TYPE_TO_CLASS[step_type]
        return clz.from_dict(step_data)

    @staticmethod
    def base_fields(base_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        加载各个步骤的基础字段
        """
        return {
            "id": base_data['id'],
            "type": FlowStepType(base_data['type']),
            "description": base_data.get('description', ''),
            "next": FlowStep.build_links(base_data['next'])
        }

    @staticmethod
    def build_links(link_data: str | list[Dict[str, Any]]) -> List[FlowStepLink]:
        if isinstance(link_data, str):
            return [StaticLink(target=link_data)]
        else:
            links = []
            for link_dict in link_data:
                if "if" in link_dict:
                    links.append(ConditionalLink(condition=link_dict['if'], target=link_dict['then']))
                else:
                    links.append(FallbackLink(target=link_dict['else']))
            return links


class StartFlowStep(FlowStep):
    """
    流程的步骤：开始
    """
    type: FlowStepType = FlowStepType.START
    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "StartFlowStep":
        return cls(**FlowStep.base_fields(step_data))

class EndFlowStep(FlowStep):
    """
    流程步骤：结束
    """
    type: FlowStepType = FlowStepType.END
    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "EndFlowStep":
        return cls(**FlowStep.base_fields(step_data))

class ActionFlowStep(FlowStep):
    """
    流程步骤：执行某一个动作
    """
    type: FlowStepType = FlowStepType.ACTION
    action:str
    args:dict | str = {}

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "ActionFlowStep":
        return cls(**FlowStep.base_fields(step_data),
                   action=step_data['action'],
                   args=step_data.get('args', {}))

class CollectFlowStep(FlowStep):
    """
    流程步骤：收集某个槽位信息
    """
    type : FlowStepType = FlowStepType.COLLECT
    slot_name :str
    response : ResponseDefinition
    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "CollectFlowStep":
        return cls(
            **FlowStep.base_fields(step_data),
            slot_name=step_data['slot_name'],
            response=ResponseDefinition(**step_data['response'])
        )

# 多态分发
STEP_TYPE_TO_CLASS = {
    "start": StartFlowStep,
    "action": ActionFlowStep,
    "collect": CollectFlowStep,
    "end": EndFlowStep
}








