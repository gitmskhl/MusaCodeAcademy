from typing import Literal, Annotated, Union
from pydantic import BaseModel, Field

class TextBlockData(BaseModel):
    text: str = Field(min_length=1)
    

class ImageBlockData(BaseModel):
    file_id: int = Field(gt=0)
    width: int = Field(ge=10, le=100, default=100)
    caption: str | None = None


class CodeBlockData(BaseModel):
    language: Literal["python"]
    code: str = Field(min_length=1)


class TextBlock(BaseModel):
    type: Literal["text"]
    data: TextBlockData
    

class ImageBlock(BaseModel):
    type: Literal["image"]
    data: ImageBlockData


class CodeBlock(BaseModel):
    type: Literal["code"]
    data: CodeBlockData


StepBlock = Annotated[
    Union[TextBlock, ImageBlock, CodeBlock],
    Field(discriminator="type")
]