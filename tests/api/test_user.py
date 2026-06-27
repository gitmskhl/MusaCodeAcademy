import pytest
from fastapi import status
from app.core.config import settings
from app.core.security import create_access_token
from app.enums import UserRole

@pytest.mark.asyncio
async def test_get_me_success(client, auth_headers, user_data):
    response = await client.get(
        "/api/users/me",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    
    assert data.get("id") is not None
    assert data.get("email") == user_data["email"].lower()
    assert data.get("first_name") == user_data["first_name"]
    assert data.get("last_name") == user_data["last_name"]
    assert data.get("role") == UserRole.STUDENT
    assert "last_login_at" in data
    assert "created_at" in data
    assert "updated_at" in data
    
    
@pytest.mark.asyncio
async def test_get_me_invalid_token(client, auth_headers):
    token = auth_headers["Authorization"].split()[1]
    auth_headers["Authorization"] = f"Bearer {token[::-1]}"
    response = await client.get(
        "/api/users/me",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid or expired token"
    }
    
    
@pytest.mark.asyncio
async def test_get_me_expired_token(client, auth_expired_token_headers):
    response = await client.get(
        "/api/users/me",
        headers=auth_expired_token_headers
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid or expired token"
    }
    
    
@pytest.mark.asyncio
async def test_get_me_wrong_user_id(client, auth_headers):
    fake_token = create_access_token(user_id=99999)
    auth_headers["Authorization"] = f"Bearer {fake_token}"
    response = await client.get(
        "/api/users/me",
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "User not found"
    }