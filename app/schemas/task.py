from pydantic import BaseModel, ConfigDict, Field

class TaskCreate(BaseModel):
    step_id: int
    starter_code: str | None = Field(default=None, min_length=1)
    time_limit_ms: int = Field(default=1000, gt=0, le=30000)
    memory_limit_mb: int = Field(default=128, gt=0, le=1024)


class TaskUpdate(BaseModel):
    starter_code: str | None = Field(default=None, min_length=1)
    time_limit_ms: int | None = Field(default=None, gt=0, le=30000)
    memory_limit_mb: int | None = Field(default=None, gt=0, le=1024)


class TaskPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_id: int
    starter_code: str | None
    time_limit_ms: int
    memory_limit_mb: int
