import pytest
from fastapi import status

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
        "detail": "User with this email already exists"
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
