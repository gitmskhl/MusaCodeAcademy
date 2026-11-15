from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AIHintUsage(Base):
    __tablename__ = "ai_hint_usage"
    __table_args__ = (CheckConstraint("requests_count >= 0", name="ck_ai_hint_usage_count"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    requests_count: Mapped[int] = mapped_column(Integer, nullable=False)


class AIModelHintUsage(Base):
    __tablename__ = "ai_model_hint_usage"
    __table_args__ = (CheckConstraint("requests_count >= 0", name="ck_ai_model_hint_usage_count"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    model: Mapped[str] = mapped_column(String(255), primary_key=True)
    requests_count: Mapped[int] = mapped_column(Integer, nullable=False)
