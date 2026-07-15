import hashlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import PasswordResetToken
from app.models.user import User
from app.schemas.user import UserCreate
from app.services import auth as service_auth
from app.services.auth import (
    create_password_reset_token,
    email_exists,
    get_user_id,
    register_user,
)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


async def create_test_user(db, email: str) -> User:
    return await register_user(
        UserCreate(
            email=email,
            password="12345678",
            first_name="Alex",
            last_name="Black",
        ),
        db,
    )


@pytest.mark.asyncio
async def test_email_exists_returns_false(db):
    email = "notexist@gmail.com"
    
    result = await email_exists(email, db)
    
    assert result is False
    
    
@pytest.mark.asyncio
async def test_email_exists_returns_true(db):
    email = "exist@gmail.com"
    hashed = hash_password("12yhdo2i3udf")
    first_name="Someone"
    last_name="Anyone"
    user = User(
        email=email,
        password_hash=hashed,
        first_name=first_name,
        last_name=last_name
    )
    db.add(user)
    await db.commit()
    
    result = await email_exists(email, db)
    
    assert result is True
    
    
@pytest.mark.asyncio
async def test_register_user_success(db):
    email = "TEST@example.com"
    password = "12345678"
    first_name = "Alex"
    last_name = "Black"
    user_data = UserCreate(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    
    user = await register_user(user_data, db)
    
    assert user.id is not None
    assert user.email != email
    assert user.email == email.lower()
    assert user.password_hash != password
    assert verify_password(password, user.password_hash)
    assert user.first_name == first_name
    assert user.last_name == last_name


@pytest.mark.asyncio
async def test_password_operations_are_offloaded(db, monkeypatch):
    offloaded_functions = []

    async def run_in_worker(func, *args):
        offloaded_functions.append(func)
        return func(*args)

    monkeypatch.setattr(
        service_auth,
        "asyncio",
        SimpleNamespace(to_thread=run_in_worker),
    )
    user_data = UserCreate(
        email="worker@example.com",
        password="12345678",
        first_name="Alex",
        last_name="Black",
    )

    user = await register_user(user_data, db)
    user_id = await get_user_id(user_data.email, user_data.password, db)

    assert user_id == user.id
    assert offloaded_functions == [hash_password, verify_password]
    
        
@pytest.mark.asyncio
async def test_register_user_duplicate_email(db):
    email1 = "TEST@example.com"
    password1 = "12345678"
    first_name1 = "Alex"
    last_name1 = "Black"
    user_data1 = UserCreate(
        email=email1,
        password=password1,
        first_name=first_name1,
        last_name=last_name1,
    )
    
    await register_user(user_data1, db)
    
    email2 = email1
    password2 = "56gfhlfkdgeokrt"
    first_name2 = "Jhon"
    last_name2 = "White"
    user_data2 = UserCreate(
        email=email2,
        password=password2,
        first_name=first_name2,
        last_name=last_name2,
    )
    
    with pytest.raises(HTTPException) as exc:
        await register_user(user_data2, db)
    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == "User with this email already exists"
    
    
@pytest.mark.asyncio
async def test_get_user_id_success(db):
    email = "ADMIN@mail.com"
    password = "kfg;fskgsdfg,sfg"
    first_name = "Kate"
    last_name = "Goldberg"
    user_data = UserCreate(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    
    user = await register_user(user_data, db)
    
    id = await get_user_id(email, password, db, refresh_last_login_at=False)
    assert id == user.id
    
    
@pytest.mark.asyncio
async def test_get_user_id_wrong_password(db):
    email = "ADMIN@mail.com"
    password = "kfg;fskgsdfg,sfg"
    first_name = "Kate"
    last_name = "Goldberg"
    user_data = UserCreate(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    
    await register_user(user_data, db)
    
    id = await get_user_id(email, password[::-1], db, refresh_last_login_at=False)
    assert id is None
    
    
@pytest.mark.asyncio
async def test_get_user_id_unknown_email(db):
    email = "ADMIN@mail.com"
    password = "kfg;fskgsdfg,sfg"
    first_name = "Kate"
    last_name = "Goldberg"
    user_data = UserCreate(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    
    await register_user(user_data, db)
    
    id = await get_user_id(email[::-1], password, db, refresh_last_login_at=False)
    assert id is None
    
    
@pytest.mark.asyncio
async def test_get_user_id_not_refresh_last_login_at(db):
    email = "ADMIN@mail.com"
    password = "kfg;fskgsdfg,sfg"
    first_name = "Kate"
    last_name = "Goldberg"
    user_data = UserCreate(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    
    user = await register_user(user_data, db)
    
    assert user.last_login_at is None
    
    
    
@pytest.mark.asyncio
async def test_get_user_id_refresh_last_login_at(db):
    email = "ADMIN@mail.com"
    password = "kfg;fskgsdfg,sfg"
    first_name = "Kate"
    last_name = "Goldberg"
    user_data = UserCreate(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    
    user = await register_user(user_data, db)
    id = await get_user_id(email, password, db, refresh_last_login_at=True)
    await db.refresh(user)
    
    assert id == user.id
    assert user.last_login_at is not None


@pytest.mark.asyncio
async def test_create_password_reset_token_success(db):
    user = await create_test_user(db, "password-reset@example.com")

    token = await create_password_reset_token(user, db)

    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    stored_tokens = result.scalars().all()

    assert isinstance(token, str)
    assert token
    assert len(stored_tokens) == 1

    stored_token = stored_tokens[0]
    expected_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert stored_token.token_hash != token
    assert stored_token.token_hash == expected_hash
    assert as_utc(stored_token.expires_at) > datetime.now(UTC)


@pytest.mark.asyncio
async def test_create_password_reset_token_removes_old_tokens(db):
    user = await create_test_user(db, "replace-reset-tokens@example.com")
    old_hashes = {
        hashlib.sha256(b"old-token-one").hexdigest(),
        hashlib.sha256(b"old-token-two").hexdigest(),
    }
    expires_at = datetime.now(UTC) + timedelta(minutes=5)
    db.add_all(
        [
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
            for token_hash in old_hashes
        ]
    )
    await db.commit()

    token = await create_password_reset_token(user, db)

    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    stored_tokens = result.scalars().all()

    assert len(stored_tokens) == 1
    assert stored_tokens[0].token_hash not in old_hashes
    assert stored_tokens[0].token_hash == hashlib.sha256(token.encode("utf-8")).hexdigest()


@pytest.mark.asyncio
async def test_create_password_reset_token_expiration(db):
    user = await create_test_user(db, "reset-token-expiration@example.com")
    before_creation = datetime.now(UTC)

    await create_password_reset_token(user, db)

    after_creation = datetime.now(UTC)
    stored_token = await db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    assert stored_token is not None

    expected_expiration = before_creation + timedelta(
        minutes=settings.password_reset_token_expire_minutes
    )
    latest_expected_expiration = after_creation + timedelta(
        minutes=settings.password_reset_token_expire_minutes
    )
    actual_expiration = as_utc(stored_token.expires_at)

    tolerance = timedelta(seconds=3)
    assert expected_expiration - tolerance <= actual_expiration
    assert actual_expiration <= latest_expected_expiration + tolerance
