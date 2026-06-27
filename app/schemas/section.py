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
    ordered_section_ids: list[int]