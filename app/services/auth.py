import asyncio
import secrets
import hashlib
from datetime import datetime, UTC, timedelta
from fastapi import HTTPException, status
from sqlalchemy import exists, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, PasswordResetToken
from app.services.email import send_password_reset_email
from app.schemas.user import UserCreate
from app.core.config import settings
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


async def _remove_password_reset_tokens(user_id: int, db: AsyncSession) -> None:
    await db.execute(
        delete(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id)
    )


def _generate_password_reset_token() -> str:
    token = secrets.token_urlsafe(settings.password_reset_token_length)
    return token


def _hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _get_password_reset_token_expiration() -> datetime:
    return datetime.now(UTC) + timedelta(minutes=settings.password_reset_token_expire_minutes)


async def create_password_reset_token(user: User, db: AsyncSession) -> str:
    try:
        await _remove_password_reset_tokens(user_id=user.id, db=db)
        token = _generate_password_reset_token()
        token_hash = _hash_password_reset_token(token=token)
        new_password_reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=_get_password_reset_token_expiration()
        )
        db.add(new_password_reset_token)
        await db.commit()
        return token
    except Exception:
        await db.rollback()
        raise


async def request_password_reset(
    email: str,
    db: AsyncSession
) -> None:
    email_lower = email.lower()
    user =  await db.scalar(
        select(User)
            .where(User.email == email_lower)
    )
    if not user:
        return
    token = await create_password_reset_token(user=user, db=db)
    await send_password_reset_email(
        email=user.email,
        token=token
    )


async def verify_password_reset_token(token: str, db: AsyncSession) -> PasswordResetToken:
    token_hash = _hash_password_reset_token(token=token)
    
    password_reset_token = await db.scalar(
        select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
    )

    if not password_reset_token or password_reset_token.expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token"
        )
    
    return password_reset_token

