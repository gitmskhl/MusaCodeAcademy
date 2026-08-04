from html.parser import HTMLParser
from typing import Literal, Annotated, Union
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel, Field, field_validator


class _IframeSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.src: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if self.src is not None or tag.lower() != "iframe":
            return

        for name, value in attrs:
            if name.lower() == "src" and value:
                self.src = value
                return


def _extract_embed_url(value: str) -> str:
    value = value.strip()
    if "<iframe" not in value.lower():
        return value

    parser = _IframeSrcParser()
    parser.feed(value)
    if not parser.src:
        raise ValueError("Video iframe must include a src attribute")

    return parser.src.strip()


def _normalize_kinescope_embed_url(value: str) -> str:
    embed_url = _extract_embed_url(value)
    parsed = urlparse(embed_url)

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Video URL is invalid") from exc

    embed_id = (
        parsed.path.removeprefix("/embed/")
        if parsed.path.startswith("/embed/")
        else ""
    )
    if (
        parsed.scheme.lower() != "https"
        or (parsed.hostname or "").lower() != "kinescope.io"
        or port is not None
        or not embed_id.strip("/")
    ):
        raise ValueError("Video URL must be a Kinescope embed URL")

    return urlunparse(
        (
            "https",
            "kinescope.io",
            parsed.path,
            "",
            parsed.query,
            "",
        )
    )


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

        return _normalize_kinescope_embed_url(value)


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


class VideoBlock(BaseModel):
    type: Literal["video"]
    data: VideoBlockData


StepBlock = Annotated[
    Union[TextBlock, ImageBlock, CodeBlock, CalloutBlock, VideoBlock],
    Field(discriminator="type")
]
