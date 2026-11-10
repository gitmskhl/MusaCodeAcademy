from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.enums import SubmissionStatus, UserRole


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


class AdminUserListItem(AdminUser):
    last_activity_at: datetime | None
    submissions_count: int
    solved_tasks_count: int


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


class AdminCourseOption(BaseModel):
    id: int
    title: str
