from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.enums import SubmissionStatus
from typing import Literal


class LocalSubmissionResult(BaseModel):
    status: Literal[
        SubmissionStatus.ACCEPTED,
        SubmissionStatus.WRONG_ANSWER,
        SubmissionStatus.RUNTIME_ERROR,
        SubmissionStatus.TIME_LIMIT_EXCEEDED,
        SubmissionStatus.MEMORY_LIMIT_EXCEEDED,
    ]
    passed_tests: int = Field(ge=0)
    failed_test_id: int | None = Field(default=None, gt=0)
    actual_output: str | None = Field(default=None, max_length=10000)


class SubmissionCreate(BaseModel):
    task_id: int = Field(gt=0)
    source_code: str = Field(min_length=3)
    local_result: LocalSubmissionResult | None = None


class SubmissionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    source_code: str
    passed_tests: int
    total_tests: int | None
    failed_test_id: int | None
    actual_output: str | None
    status: SubmissionStatus
    submitted_at: datetime


class SubmissionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    status: SubmissionStatus
    submitted_at: datetime

