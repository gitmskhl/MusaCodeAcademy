from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SectionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    course_id: int
    title: str
    description: str | None
    order: int
    
    
class SectionAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    course_id: int
    title: str
    description: str | None
    order: int
    created_at: datetime
    updated_at: datetime


class SectionCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    
    
class SectionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10)


class SectionOrderUpdate(BaseModel):
    id: int
    order: int = Field(ge=0, description="The new order of the section. Must be a non-negative integer.")
    
    
class SectionOrderUpdateList(BaseModel):
    sections: list[SectionOrderUpdate]