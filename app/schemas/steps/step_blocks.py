from typing import Literal, Annotated, Union
from pydantic import BaseModel, Field

class TextBlockData(BaseModel):
    text: str = Field(min_length=1)
    

class ImageBlockData(BaseModel):
    file_id: int = Field(gt=0)
    width: float = Field(ge=20, le=100, default=100.0)
    caption: str | None = None


class CodeBlockData(BaseModel):
    language: Literal["python"]
    code: str = Field(min_length=1)


class CalloutData(BaseModel):
    variant: Literal["info", "tip", "important", "warning", "error"]
    content: str


class TextBlock(BaseModel):
    type: Literal["text"]
    data: TextBlockData
    

class ImageBlock(BaseModel):
    type: Literal["image"]
    data: ImageBlockData


class CodeBlock(BaseModel):
    type: Literal["code"]
    data: CodeBlockData


class CalloutBlock(BaseModel):
    type: Literal["callout"]
    data: CalloutData


StepBlock = Annotated[
    Union[TextBlock, ImageBlock, CodeBlock, CalloutBlock],
    Field(discriminator="type")
]