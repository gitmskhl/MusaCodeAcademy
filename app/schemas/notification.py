from datetime import date, datetime
from typing import Annotated, Literal
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Message = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10000)]
StudentId = Annotated[int, Field(strict=True, gt=0, le=2_147_483_647)]


class RecipientSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_mode: Literal["all", "selected"]
    recipient_ids: list[StudentId] = Field(default_factory=list, max_length=10000)

    @model_validator(mode="after")
    def validate_selection(self):
        self.recipient_ids = list(dict.fromkeys(self.recipient_ids))
        if self.recipient_mode == "selected" and not self.recipient_ids:
            raise ValueError("Выберите хотя бы одного ученика")
        if self.recipient_mode == "all" and self.recipient_ids:
            raise ValueError("Для отправки всем не нужно указывать отдельных учеников")
        return self


class NotificationCreate(RecipientSelection):
    title: Title
    text: Message


class RecipientCount(BaseModel):
    count: int


class StudentOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str
    email: str


class StudentOptionPage(BaseModel):
    items: list[StudentOption]
    total: int
    page: int
    page_size: int


class HomeworkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title = "Новое домашнее задание"
    comment: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=10000)] = None
    url: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2048)]
    due_date: date | None = None

    @field_validator("comment")
    @classmethod
    def empty_comment(cls, value):
        return value or None

    @field_validator("url")
    @classmethod
    def safe_url(cls, value: str) -> str:
        decoded = unquote(value)
        if any(ord(char) <= 32 or ord(char) == 127 or char == "\\" for char in value):
            raise ValueError("Ссылка не должна содержать пробелы, управляющие символы или обратный слеш")
        if "\\" in decoded or any(ord(char) < 32 or ord(char) == 127 for char in decoded):
            raise ValueError("Недопустимые символы в ссылке")
        if value.startswith("/") and not decoded.startswith("//"):
            return value
        try:
            parsed = urlsplit(value)
            valid = parsed.scheme.lower() in {"http", "https"} and bool(parsed.hostname) and parsed.port != 0
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Укажите внутренний путь сайта или полный адрес http/https")
        return value


class HomeworkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    comment: str | None
    url: str
    due_date: date | None
    created_at: datetime


class HomeworkPage(BaseModel):
    items: list[HomeworkRead]
    total: int
    page: int
    page_size: int


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    text: str
    created_at: datetime
    read_at: datetime | None
    homework: HomeworkRead | None


class NotificationPage(BaseModel):
    items: list[NotificationRead]
    total: int
    unread_count: int
    page: int
    page_size: int
