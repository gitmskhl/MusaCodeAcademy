from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.enums import SubmissionStatus, UserRole
from app.schemas.notification import HomeworkRead


class AdminUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str
    last_name: str
    role: UserRole
    created_at: datetime
    last_login_at: datetime | None
    blocked_at: datetime | None
    block_reason: str | None
    ai_assistance_enabled: bool
    ai_daily_limit: int
    ai_model_limits: dict[str, int] | None


class AdminHomeworkDeadline(BaseModel):
    id: int
    due_date: date | None


class AdminUserListItem(AdminUser):
    last_activity_at: datetime | None
    submissions_count: int
    solved_tasks_count: int
    latest_homework: AdminHomeworkDeadline | None


class AdminUserPage(BaseModel):
    items: list[AdminUserListItem]
    total: int
    page: int
    page_size: int


class AdminCourseProgress(BaseModel):
    id: int
    title: str
    is_published: bool
    enrolled: bool
    completed_steps: int
    total_steps: int
    solved_tasks: int
    total_tasks: int
    submissions_count: int
    last_activity_at: datetime | None


class AdminUserDetail(AdminUserListItem):
    courses: list[AdminCourseProgress]


class UserBlockUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocked: bool
    reason: str | None = Field(default=None, max_length=500)


class UserAIAssistanceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    daily_limit: int | None = Field(default=None, ge=1, le=1000)
    model_limits: dict[
        Annotated[str, Field(min_length=1, max_length=255)],
        Annotated[int, Field(strict=True, ge=1, le=1000)],
    ] | None = Field(default=None, max_length=100)


class AdminSubmissionItem(BaseModel):
    id: int
    user_id: int
    user_name: str
    user_email: str
    task_id: int
    step_id: int
    step_title: str
    lesson_title: str
    course_id: int
    course_slug: str
    course_title: str
    status: SubmissionStatus
    submitted_at: datetime
    passed_tests: int
    total_tests: int | None


class AdminSubmissionPage(BaseModel):
    items: list[AdminSubmissionItem]
    total: int
    page: int
    page_size: int


class AdminSubmissionDetail(AdminSubmissionItem):
    source_code: str
    failed_test_id: int | None
    actual_output: str | None
    ai_hint: str | None
    ai_hint_model: str | None


class AdminCourseOption(BaseModel):
    id: int
    title: str
    is_published: bool


class AdminHomeworkStep(BaseModel):
    id: int
    title: str
    position: int
    url: str
    task_id: int | None
    status: Literal["solved", "attempted", "checking", "not_started", "completed"]
    submissions_count: int


class AdminHomeworkProgress(BaseModel):
    homework: HomeworkRead | None
    unavailable_reason: str | None = None
    course_title: str | None = None
    lesson_title: str | None = None
    steps: list[AdminHomeworkStep] = Field(default_factory=list)
    total_tasks: int = 0
    solved_tasks: int = 0
    submissions: AdminSubmissionPage
