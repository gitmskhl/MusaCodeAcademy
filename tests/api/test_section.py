import pytest
from fastapi import status


PUBLIC_SECTION_FIELDS = {
    "id",
    "course_id",
    "title",
    "description",
    "order",
}
ADMIN_SECTION_FIELDS = PUBLIC_SECTION_FIELDS | {
    "created_at",
    "updated_at",
}


@pytest.mark.asyncio
async def test_get_section_success(client, section_factory):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
        title="Simple section",
        description="Simple section descr"
    )
    response = await client.get(
        f"/api/sections/{section.id}"
    )
    assert response.status_code == status.HTTP_200_OK
    sectionInfo = response.json()
    assert set(sectionInfo) == PUBLIC_SECTION_FIELDS
    assert sectionInfo["id"] == section.id
    assert sectionInfo["course_id"] == section.course_id
    assert sectionInfo["title"] == "Simple section"
    assert sectionInfo["description"] == "Simple section descr"
    assert sectionInfo["order"] == 0
    

@pytest.mark.asyncio
async def test_get_section_course_not_published_error_404(client, section_factory):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
        title="Simple section",
        description="Simple section descr"
    )
    response = await client.get(
        f"/api/sections/{section.id}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": "Course not found"
    }
    
    
@pytest.mark.asyncio
async def test_get_section_section_not_found_error_404(client, section_factory):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
        title="Simple section",
        description="Simple section descr"
    )
    response = await client.get(
        f"/api/sections/{section.id + 1}"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": "Section not found"
    }


@pytest.mark.asyncio
async def test_get_section_rejects_invalid_id(client):
    response = await client.get("/api/sections/not-an-id")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "section_id"]


# GET /api/sections/{section_id}/admin


@pytest.mark.asyncio
async def test_get_section_admin_returns_draft(
    client,
    admin_headers,
    section_factory,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=2,
        title="Draft section",
        description="Draft section description",
    )

    response = await client.get(
        f"/api/sections/{section.id}/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert set(data) == ADMIN_SECTION_FIELDS
    assert data["id"] == section.id
    assert data["course_id"] == section.course_id
    assert data["title"] == section.title
    assert data["description"] == section.description
    assert data["order"] == section.order
    assert data["created_at"]
    assert data["updated_at"]


@pytest.mark.asyncio
async def test_get_section_admin_not_found(client, admin_headers):
    response = await client.get(
        "/api/sections/999999/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Section not found"}


@pytest.mark.asyncio
async def test_get_section_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )

    response = await client.get(
        f"/api/sections/{section.id}/admin",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_get_section_admin_requires_authentication(
    client,
    section_factory,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )

    response = await client.get(f"/api/sections/{section.id}/admin")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_get_section_admin_rejects_invalid_id(client, admin_headers):
    response = await client.get(
        "/api/sections/not-an-id/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "section_id"]


# DELETE /api/sections/{section_id}/admin


@pytest.mark.asyncio
async def test_delete_section_admin_success(
    client,
    admin_headers,
    section_factory,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )

    response = await client.delete(
        f"/api/sections/{section.id}/admin",
        headers=admin_headers,
    )
    get_response = await client.get(
        f"/api/sections/{section.id}/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert get_response.status_code == status.HTTP_404_NOT_FOUND
    assert get_response.json() == {"detail": "Section not found"}


@pytest.mark.asyncio
async def test_delete_section_admin_not_found(client, admin_headers):
    response = await client.delete(
        "/api/sections/999999/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Section not found"}


@pytest.mark.asyncio
async def test_delete_section_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )

    response = await client.delete(
        f"/api/sections/{section.id}/admin",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_delete_section_admin_requires_authentication(
    client,
    section_factory,
):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )

    response = await client.delete(f"/api/sections/{section.id}/admin")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_delete_section_admin_rejects_invalid_id(
    client,
    admin_headers,
):
    response = await client.delete(
        "/api/sections/not-an-id/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "section_id"]


@pytest.mark.asyncio
async def test_update_section_success(client, section_factory, admin_headers):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    response = await client.patch(
        f"/api/sections/{section.id}/admin",
        headers=admin_headers,
        json={
            "title": "New title",
            "description": "New description"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "New title"
    assert data["description"] == "New description"
    
    
@pytest.mark.asyncio
async def test_update_section_success_title(client, section_factory, admin_headers):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    response = await client.patch(
        f"/api/sections/{section.id}/admin",
        headers=admin_headers,
        json={
            "title": "New title"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == "New title"
    assert data["description"] == section.description
    
    
@pytest.mark.asyncio
async def test_update_section_success_description(client, section_factory, admin_headers):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    response = await client.patch(
        f"/api/sections/{section.id}/admin",
        headers=admin_headers,
        json={
            "description": "New description"
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == section.title
    assert data["description"] == "New description"
    
    
@pytest.mark.asyncio
async def test_update_section_not_found(client, admin_headers):
    response = await client.patch(
        "/api/sections/999999/admin",
        headers=admin_headers,
        json={
            "title": "New title",
            "description": "New description"
        }
    )
    
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Section not found"}
    

@pytest.mark.asyncio
async def test_update_section_rejects_non_admin(client, auth_headers, section_factory):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    response = await client.patch(
        f"/api/sections/{section.id}/admin",
        headers=auth_headers,
        json={
            "title": "New title",
            "description": "New description"
        }
    )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }