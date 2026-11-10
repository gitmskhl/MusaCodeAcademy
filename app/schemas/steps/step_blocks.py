from typing import Literal, Annotated, Union

from pydantic import BaseModel, Field, field_validator
from app.schemas.video import normalize_kinescope_embed_url


class TextBlockData(BaseModel):
    text: str = Field(min_length=1)
    

class ImageBlockData(BaseModel):
    file_id: int = Field(gt=0)
    width: float = Field(ge=20, le=100, default=100.0)
    caption: str | None = None


class CodeBlockData(BaseModel):
    language: Literal["python"]
    code: str = Field(min_length=1)


class BrowserPythonBlockData(BaseModel):
    code: str = Field(min_length=1)
    stdin: str = ""


class ConsoleLineData(BaseModel):
    type: Literal["output", "input"]
    text: str


class ConsoleBlockData(BaseModel):
    lines: list[ConsoleLineData] = Field(default_factory=list)


class CalloutData(BaseModel):
    variant: Literal["info", "tip", "important", "warning", "error"]
    title: str | None
    content: str


class VideoBlockData(BaseModel):
    provider: Literal["kinescope"] = "kinescope"
    embed_url: str = Field(min_length=1, max_length=2048)
    title: str | None = Field(default=None, max_length=255)
    caption: str | None = Field(default=None, max_length=255)
    aspect_ratio: Literal["16:9", "4:3", "1:1", "9:16"] = "16:9"

    @field_validator("embed_url", mode="before")
    @classmethod
    def validate_embed_url(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        return normalize_kinescope_embed_url(value)


class TextBlock(BaseModel):
    type: Literal["text"]
    data: TextBlockData
    

class ImageBlock(BaseModel):
    type: Literal["image"]
    data: ImageBlockData


class CodeBlock(BaseModel):
    type: Literal["code"]
    data: CodeBlockData


class BrowserPythonBlock(BaseModel):
    type: Literal["browser_python"]
    data: BrowserPythonBlockData


class ConsoleBlock(BaseModel):
    type: Literal["console"]
    data: ConsoleBlockData


class CalloutBlock(BaseModel):
    type: Literal["callout"]
    data: CalloutData


class VideoBlock(BaseModel):
    type: Literal["video"]
    data: VideoBlockData


StepBlock = Annotated[
    Union[
        TextBlock,
        ImageBlock,
        CodeBlock,
        BrowserPythonBlock,
        ConsoleBlock,
        CalloutBlock,
        VideoBlock,
    ],
    Field(discriminator="type")
]
