import asyncio
from datetime import datetime, UTC
from fastapi import HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password

async def email_exists(email: str, db: AsyncSession) -> bool:
    return bool(
        await db.scalar(
            select(exists().where(User.email == email.lower()))
        )
    )


async def get_user_id(
        email: str,
        password: str,
        db: AsyncSession,
        refresh_last_login_at: bool = False
    ) -> int | None:
    result = await db.execute(
        select(User).where(
            User.email == email.lower()
        )
    )
    user = result.scalars().first()
    
    if not user:
        return None

    password_is_valid = await asyncio.to_thread(
        verify_password,
        password,
        user.password_hash,
    )
    if not password_is_valid:
        return None
    
    if refresh_last_login_at:
        user.last_login_at = datetime.now(UTC)
        await db.commit()
    return user.id


async def register_user(user: UserCreate, db: AsyncSession) -> User:
    email_taken = await email_exists(user.email, db)
    if email_taken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
        
    password_hash = await asyncio.to_thread(hash_password, user.password)

    new_user = User(
        email=user.email.lower(),
        password_hash=password_hash,
        first_name=user.first_name,
        last_name=user.last_name
    )
    db.add(new_user)
    try:
        await db.commit()
        return new_user
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
