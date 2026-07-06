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


class StepNavigation(BaseModel):
    position: int
    total: int
    previous_step_id: int | None
    next_step_id: int | None


class StepSummary(BaseModel):
    id: int
    title: str


class StepViewerLesson(BaseModel):
    id: int
    section_id: int
    title: str
    steps: list[StepSummary]


class StepViewer(BaseModel):
    step: StepPublic
    navigation: StepNavigation
    lesson: StepViewerLesson
    

class StepUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: StepContent | None = None
    

class StepOrderUpdate(BaseModel):
    id: int
    order: int = Field(ge=0, description="The new order of the lesson. Must be a non-negative integer.")
    
    
class StepOrderUpdateList(BaseModel):
    steps: list[StepOrderUpdate]
