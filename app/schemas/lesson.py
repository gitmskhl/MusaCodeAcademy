from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class LessonPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    section_id: int
    title: str
    description: str | None
    order: int


class LessonAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    section_id: int
    title: str
    description: str | None
    order: int
    created_at: datetime
    updated_at: datetime
    
    
class LessonCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    

class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    
    
class LessonOrderUpdate(BaseModel):
    id: int
    order: int = Field(ge=0, description="The new order of the lesson. Must be a non-negative integer.")
    
    
class LessonOrderUpdateList(BaseModel):
    lessons: list[LessonOrderUpdate]
