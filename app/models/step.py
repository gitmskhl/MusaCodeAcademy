from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime, UTC
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from .task import Task
    from .lesson import Lesson


class Step(Base):
    __tablename__ = "steps"
    __table_args__ = (
        Index("ix_steps_lesson_id_order", "lesson_id", "order"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    content: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    task: Mapped["Task"] = relationship(
        back_populates="step",
        cascade="all, delete-orphan"
    )

    lesson: Mapped["Lesson"] = relationship(
        back_populates="steps"
    )