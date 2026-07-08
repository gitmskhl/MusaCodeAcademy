from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ConfigDict, field_validator
from .section import SectionShortInfo


class CourseEditableFields(BaseModel):
    level: str = Field(default="Начинающий", min_length=2, max_length=80)
    price_label: str = Field(default="Бесплатно", min_length=2, max_length=120)
    outcomes: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("level", "price_label")
    @classmethod
    def strip_label(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("outcomes", mode="before")
    @classmethod
    def normalize_outcomes(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("Outcomes must be a list")

        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("Each outcome must be a string")

            normalized = item.strip()
            if not normalized:
                continue
            if len(normalized) > 120:
                raise ValueError("Each outcome must be 120 characters or fewer")

            cleaned.append(normalized)

        return cleaned


class CourseCreate(CourseEditableFields):
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
    level: str
    price_label: str
    outcomes: list[str] = Field(default_factory=list)
    
    
class CourseAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    slug: str
    
    short_description: str
    description: str
    level: str
    price_label: str
    outcomes: list[str] = Field(default_factory=list)
    
    is_published: bool
    created_at: datetime
    updated_at: datetime
    
    
class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    
    short_description: str | None = Field(default=None, min_length=10)
    description: str | None = Field(default=None, min_length=20)
    level: str | None = Field(default=None, min_length=2, max_length=80)
    price_label: str | None = Field(default=None, min_length=2, max_length=120)
    outcomes: list[str] | None = Field(default=None, max_length=12)
    is_published: bool | None = Field(default=None)

    @field_validator("level", "price_label")
    @classmethod
    def strip_optional_label(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("outcomes", mode="before")
    @classmethod
    def normalize_optional_outcomes(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        return CourseEditableFields.normalize_outcomes(value)


class CourseInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    title: str
    slug: str
    
    short_description: str
    description: str
    level: str
    price_label: str
    outcomes: list[str] = Field(default_factory=list)
    lessons_count: int = 0
    sections_count: int = 0

    is_enrolled: bool = False
    sections: list[SectionShortInfo] = Field(default_factory=list)
