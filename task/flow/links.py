from pydantic import BaseModel

class FlowStepLink(BaseModel):
    """
    模版边（基类）
    """
    target:str

class StaticLink(FlowStepLink):
    """
    静态边
    """
    pass

class ConditionalLink(FlowStepLink):
    """
    条件边
    """
    condition:str

class FallbackLink(FlowStepLink):
    """
    备用边
    """
    pass