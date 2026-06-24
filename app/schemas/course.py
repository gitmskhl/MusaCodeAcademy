from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CourseCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    slug: str = Field(min_length=2, max_length=255)
    
    short_description: str = Field(min_length=10)
    description: str = Field(min_length=20)
    

class CoursePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    slug: str
    
    short_description: str
    description: str
    
    
class CoursePrivate(BaseModel):
    id: int
    title: str
    slug: str
    
    short_description: str
    description: str
    
    is_published: bool
    created_at: datetime
    updated_at: datetime
    
    
class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    
    short_description: str | None = Field(default=None, min_length=10)
    description: str | None = Field(default=None, min_length=20)