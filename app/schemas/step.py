from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TextBlockData(BaseModel):
    text: str = Field(min_length=1)
    

class ImageBlockData(BaseModel):
    url: str = Field(min_length=1)
    alt: str | None = None
    caption: str | None = None


class TextBlock(BaseModel):
    type: Literal["text"]
    data: TextBlockData
    

class ImageBlock(BaseModel):
    type: Literal["image"]
    data: ImageBlockData
    
    
StepBlock = Annotated[
    Union[TextBlock, ImageBlock],
    Field(discriminator="type")
]


class VerticalStepContent(BaseModel):
    layout: Literal["vertical"]
    blocks: list[StepBlock] = Field(default_factory=list)


class TwoColumnsStepContent(BaseModel):
    layout: Literal["two_columns"]
    left: list[StepBlock] = Field(default_factory=list)
    right: list[StepBlock] = Field(default_factory=list)
    
    
StepContent = Annotated[
    Union[VerticalStepContent, TwoColumnsStepContent],
    Field(discriminator="layout")
]


class StepCreate(BaseModel):
    lesson_id: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=255)
    order: int | None = Field(default=None, ge=1)
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