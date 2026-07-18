from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from .task import Task

class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(primary_key=True)

    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    input: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)

    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    task: Mapped["Task"] = relationship(back_populates="test_cases")