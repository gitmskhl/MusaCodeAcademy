from pydantic import BaseModel, Field, ConfigDict


class TestCaseCreate(BaseModel):
    task_id: int
    input: str | None = Field(default=None, min_length=1)
    expected_output: str = Field(min_length=1)
    is_hidden: bool = True


class TestCasePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    input: str | None
    expected_output: str
    is_hidden: bool
    order: int


class TestCaseUpdate(BaseModel):
    input: str | None = Field(default=None, min_length=1)
    expected_output: str | None = Field(default=None, min_length=1)
    is_hidden: bool | None = None
