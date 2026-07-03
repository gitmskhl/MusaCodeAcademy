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