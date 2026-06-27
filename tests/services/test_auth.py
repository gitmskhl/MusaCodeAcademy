import pytest
from fastapi import HTTPException, status
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.auth import email_exists, register_user, get_user_id


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