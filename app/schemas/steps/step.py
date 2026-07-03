from pydantic import BaseModel, ConfigDict, Field
from .step_layout import StepContent


class StepCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: StepContent
    
    
class StepPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    lesson_id: int
    title: str
    order: int
    content: StepContent
    
    
class StepAdmin(StepPublic):
    pass


class StepUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: StepContent | None = None
    

class StepOrderUpdate(BaseModel):
    id: int
    order: int = Field(ge=0, description="The new order of the lesson. Must be a non-negative integer.")
    
    
class StepOrderUpdateList(BaseModel):
    steps: list[StepOrderUpdate]