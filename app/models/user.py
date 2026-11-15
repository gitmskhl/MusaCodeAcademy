from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, Integer, JSON, String, DateTime, Enum as SQLEnum, false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, UTC

from .base import Base
from app.enums import UserRole

if TYPE_CHECKING:
    from .enrollment import Enrollment
    from .password_reset_token import PasswordResetToken

class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("ai_daily_limit BETWEEN 1 AND 1000", name="ck_users_ai_daily_limit"),)
    
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

    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    block_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_assistance_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    ai_daily_limit: Mapped[int] = mapped_column(Integer, default=10, server_default="10", nullable=False)
    ai_model_limits: Mapped[dict[str, int] | None] = mapped_column(JSON, nullable=True, default=None)
    
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

    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
