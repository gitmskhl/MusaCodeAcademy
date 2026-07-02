from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime, UTC
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.lesson import Lesson
from .base import Base

if TYPE_CHECKING:
    from .course import Course

class Section(Base):
    __tablename__ = "sections"
    
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        index=True
    )    

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    description: Mapped[str | None] = mapped_column(Text, default=None)
    
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )
    
    course: Mapped["Course"] = relationship(back_populates="sections")
    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="Lesson.order"
    )