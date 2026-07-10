from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime, UTC
from app.models.base import Base
from sqlalchemy import Integer, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .testCase import TestCase
    from .step import Step
    from .submission import Submission

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)

    step_id: Mapped[int] = mapped_column(
        ForeignKey("steps.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    time_limit_ms: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=128, nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    step: Mapped["Step"] = relationship(
        back_populates="task",
    )

    test_cases: Mapped[list["TestCase"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TestCase.order"
    )

    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )