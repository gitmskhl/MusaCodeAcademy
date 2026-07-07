from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, UTC

from .base import Base
from app.enums import UserRole

if TYPE_CHECKING:
    from .enrollment import Enrollment

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    first_name: Mapped[str] = mapped_column(String(20), nullable=False)
    last_name: Mapped[str] = mapped_column(String(20), nullable=False)
    
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.STUDENT,
        nullable=False
    )
    
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC)
    )

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
