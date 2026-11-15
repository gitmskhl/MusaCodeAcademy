from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AIModelStatus(BaseModel):
    model: str
    daily_limit: int
    remaining: int


class AIHintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(default=None, min_length=1, max_length=255)


class AIHintStatus(BaseModel):
    enabled: bool
    daily_limit: int
    remaining: int
    resets_at: datetime
    models: list[AIModelStatus]


class AIHintResponse(AIHintStatus):
    hint: str
    model: str | None
