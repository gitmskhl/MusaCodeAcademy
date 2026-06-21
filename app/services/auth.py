from datetime import datetime, UTC
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password

async def email_exists(email: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(User).where(func.lower(User.email) == email.lower())
    )
    user = result.scalars().first()
    
    if not user:
        return False
    return True


async def get_user_id(
        email: str,
        password: str,
        db: AsyncSession,
        refresh_last_login_at: bool = False
    ) -> int | None:
    result = await db.execute(
        select(User).where(
            func.lower(User.email) == email.lower()
        )
    )
    user = result.scalars().first()
    
    if not user or not verify_password(password, user.password_hash):
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
        
    new_user = User(
        email=user.email.lower(),
        password_hash=hash_password(user.password),
        first_name=user.first_name,
        last_name=user.last_name
    )
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
        return new_user
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )