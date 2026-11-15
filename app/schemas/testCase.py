from pydantic import BaseModel, ConfigDict


class TestCaseCreate(BaseModel):
    task_id: int
    input: str = ""
    expected_output: str
    is_hidden: bool = False


class TestCasePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    input: str
    expected_output: str
    is_hidden: bool
    order: int


class TestCaseUpdate(BaseModel):
    input: str = ""
    expected_output: str | None = None
    is_hidden: bool | None = None
