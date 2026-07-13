from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.enums import SubmissionStatus


class SubmissionCreate(BaseModel):
    task_id: int = Field(gt=0)
    source_code: str = Field(min_length=3)


class SubmissionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    source_code: str
    passed_tests: int
    status: SubmissionStatus
    submitted_at: datetime


class SubmissionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    status: SubmissionStatus
    submitted_at: datetime

