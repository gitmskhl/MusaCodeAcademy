from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, String, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.enums import FileType




class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)

    file_type: Mapped[FileType] = mapped_column(
        SQLEnum(FileType),
        nullable=False
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    storage_path: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    size: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )