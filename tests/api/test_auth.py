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