from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StepProgress(Base):
    __tablename__ = "step_progress"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "step_id",
            name="uq_user_step_progress",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    step_id: Mapped[int] = mapped_column(
        ForeignKey("steps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user = relationship("User")
    step = relationship("Step")