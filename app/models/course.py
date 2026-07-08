from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime, UTC
from sqlalchemy import String, Text, Boolean, DateTime, JSON
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .section import Section
    from .enrollment import Enrollment


class Course(Base):
    __tablename__ = "courses"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    level: Mapped[str] = mapped_column(String(80), default="Начинающий", nullable=False)
    price_label: Mapped[str] = mapped_column(String(120), default="Бесплатно", nullable=False)
    outcomes: Mapped[list[str]] = mapped_column(
        MutableList.as_mutable(JSON),
        default=list,
        nullable=False,
    )
    
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )

    sections: Mapped[list["Section"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Section.order"
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )
