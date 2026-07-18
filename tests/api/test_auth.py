import pytest
from fastapi import status

from app.services.auth import create_password_reset_token
from app.schemas.user import UserCreate
from app.services.auth import register_user

@pytest.mark.asyncio
async def test_register_success(client):
    email = "test@example.com"
    password = "12345678"
    first_name = "Alex"
    last_name = "Silver"
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name
        }
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert "user" in data
    assert "token" in data
    
    assert "access_token" in data["token"]
    assert "token_type" in data["token"]
    assert data["token"]["token_type"] == "bearer"
    user = data["user"]
    assert user["id"] is not None
    assert user["email"] == email
    assert user["first_name"] == first_name
    assert user["last_name"] == last_name
    assert "password" not in user
    assert "password_hash" not in user


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    email = "duplicate@example.com"
    user_data = {
        "email": email,
        "password": "12345678",
        "first_name": "Alex",
        "last_name": "Silver"
    }
    response = await client.post(
        "/api/auth/register",
        json=user_data
    )
    assert response.status_code == status.HTTP_201_CREATED

    response = await client.post(
        "/api/auth/register",
        json=user_data
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {
        "detail": "Пользователь с таким email уже существует."
    }


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "invalid-email",
            "password": "12345678",
            "first_name": "Alex",
            "last_name": "Silver"
        }
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = response.json()["detail"]
    assert len(detail) == 1
    assert detail[0]["type"] == "value_error"
    assert detail[0]["loc"] == ["body", "email"]


@pytest.mark.asyncio
async def test_register_short_password(client):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "short-password@example.com",
            "password": "1234567",
            "first_name": "Alex",
            "last_name": "Silver"
        }
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = response.json()["detail"]
    assert len(detail) == 1
    assert detail[0]["type"] == "string_too_short"
    assert detail[0]["loc"] == ["body", "password"]
    assert detail[0]["ctx"]["min_length"] == 8


@pytest.mark.asyncio
async def test_register_missing_required_fields(client):
    response = await client.post(
        "/api/auth/register",
        json={}
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = response.json()["detail"]
    assert len(detail) == 4
    assert all(error["type"] == "missing" for error in detail)
    assert {error["loc"][-1] for error in detail} == {
        "email",
        "password",
        "first_name",
        "last_name"
    }


@pytest.mark.asyncio
async def test_get_token_success(client):
    email = "test@example.com"
    password = "12345678"
    first_name = "Alex"
    last_name = "Silver"
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name
        }
    )
    
    response = await client.post(
        "/api/auth/token",
        data={
            "username": email,
            "password": password
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "access_token" in data
    assert data["access_token"] is not None
    assert "token_type" in data
    assert data["token_type"] is not None
    
    
@pytest.mark.asyncio
async def test_get_token_wrong_username(client):
    email = "test@example.com"
    password = "12345678"
    first_name = "Alex"
    last_name = "Silver"
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name
        }
    )
    
    response = await client.post(
        "/api/auth/token",
        data={
            "username": "wrong@gmail.com",
            "password": password
        }
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Неверный email или пароль."
    }
    
    
@pytest.mark.asyncio
async def test_get_token_wrong_password(client):
    email = "test@example.com"
    password = "12345678"
    first_name = "Alex"
    last_name = "Silver"
    response = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name
        }
    )
    
    response = await client.post(
        "/api/auth/token",
        data={
            "username": email,
            "password": "asdasdasdasdasdasd"
        }
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Неверный email или пароль."
    }


@pytest.mark.asyncio
async def test_verify_password_reset_token_success(client, db):
    user = await register_user(
        UserCreate(
            email="verify-reset-endpoint@example.com",
            password="12345678",
            first_name="Alex",
            last_name="Silver",
        ),
        db,
    )
    token = await create_password_reset_token(user, db)

    response = await client.get(
        "/api/auth/reset-password/verify",
        params={"token": token},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""


@pytest.mark.asyncio
async def test_verify_password_reset_token_invalid_token(client):
    response = await client.get(
        "/api/auth/reset-password/verify",
        params={"token": "unknown-token"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Invalid or expired token"}


@pytest.mark.asyncio
async def test_verify_password_reset_token_requires_token(client):
    response = await client.get("/api/auth/reset-password/verify")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_reset_password_success(client, db):
    email = "reset-password-endpoint@example.com"
    old_password = "12345678"
    new_password = "new-password-123"
    user = await register_user(
        UserCreate(
            email=email,
            password=old_password,
            first_name="Alex",
            last_name="Silver",
        ),
        db,
    )
    token = await create_password_reset_token(user, db)

    response = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""

    old_password_response = await client.post(
        "/api/auth/token",
        data={"username": email, "password": old_password},
    )
    new_password_response = await client.post(
        "/api/auth/token",
        data={"username": email, "password": new_password},
    )

    assert old_password_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert new_password_response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client):
    response = await client.post(
        "/api/auth/reset-password",
        json={
            "token": "unknown-token",
            "new_password": "new-password-123",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Invalid or expired token"}


@pytest.mark.asyncio
async def test_reset_password_rejects_short_password(client):
    response = await client.post(
        "/api/auth/reset-password",
        json={
            "token": "some-token",
            "new_password": "1234567",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = response.json()["detail"]
    assert len(detail) == 1
    assert detail[0]["type"] == "string_too_short"
    assert detail[0]["loc"] == ["body", "new_password"]
    assert detail[0]["ctx"]["min_length"] == 8


@pytest.mark.asyncio
async def test_reset_password_token_cannot_be_reused(client, db):
    user = await register_user(
        UserCreate(
            email="single-use-reset-token@example.com",
            password="12345678",
            first_name="Alex",
            last_name="Silver",
        ),
        db,
    )
    token = await create_password_reset_token(user, db)

    first_response = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "new-password-123"},
    )
    second_response = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "another-password-123"},
    )

    assert first_response.status_code == status.HTTP_204_NO_CONTENT
    assert second_response.status_code == status.HTTP_400_BAD_REQUEST
    assert second_response.json() == {"detail": "Invalid or expired token"}
