from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime, UTC
from sqlalchemy import ForeignKey, DateTime, Text, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.enums import SubmissionStatus

if TYPE_CHECKING:
    from .task import Task

class Submission(Base):
    __tablename__ = "submissions"

    __table_args__ = (
        Index(
            "ix_submission_task_user_submitted_at",
            "task_id",
            "user_id",
            "submitted_at"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False   
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    source_code: Mapped[str] = mapped_column(Text, nullable=False)

    passed_tests: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tests: Mapped[int | None] = mapped_column(Integer, default=None)
    failed_test_id: Mapped[int | None] = mapped_column(Integer, default=None)
    actual_output: Mapped[str | None] = mapped_column(Text, default=None)

    status: Mapped[SubmissionStatus] = mapped_column(default=SubmissionStatus.PENDING, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    task: Mapped["Task"] = relationship(
        back_populates="submissions"
    )
