import pytest
from fastapi import status

from app.models import Lesson


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
PUBLIC_LESSON_FIELDS = {
    "id",
    "section_id",
    "title",
    "description",
    "order",
}
ADMIN_LESSON_FIELDS = PUBLIC_LESSON_FIELDS | {
    "created_at",
    "updated_at",
}


async def enroll_in_course(client, auth_headers, course_id: int):
    response = await client.post(
        f"/api/courses/{course_id}/enroll",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED


async def create_lesson(
    db,
    *,
    section_id,
    title="Test lesson",
    description="Detailed lesson description",
    order=0,
):
    lesson = Lesson(
        section_id=section_id,
        title=title,
        description=description,
        order=order,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


@pytest.mark.asyncio
async def test_get_section_success(client, section_factory, auth_headers):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
        title="Simple section",
        description="Simple section descr"
    )
    response = await client.get(
        f"/api/sections/{section.id}",
        headers=auth_headers,
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
async def test_get_section_course_not_published_error_404(
    client,
    section_factory,
    auth_headers,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
        title="Simple section",
        description="Simple section descr"
    )
    response = await client.get(
        f"/api/sections/{section.id}",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": "Course not found"
    }
    
    
@pytest.mark.asyncio
async def test_get_section_section_not_found_error_404(
    client,
    section_factory,
    auth_headers,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
        title="Simple section",
        description="Simple section descr"
    )
    response = await client.get(
        f"/api/sections/{section.id + 1}",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": "Section not found"
    }


@pytest.mark.asyncio
async def test_get_section_rejects_invalid_id(client, auth_headers):
    response = await client.get(
        "/api/sections/not-an-id",
        headers=auth_headers,
    )

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


# PATCH /api/sections/admin/order


@pytest.mark.asyncio
async def test_update_section_orders_admin_success(
    client,
    admin_headers,
    section_factory,
):
    first_section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    second_section = await section_factory(
        course_id=first_section.course_id,
        is_published=False,
        order=1,
    )

    response = await client.patch(
        "/api/sections/admin/order",
        headers=admin_headers,
        json={
            "sections": [
                {"id": first_section.id, "order": 1},
                {"id": second_section.id, "order": 0},
            ]
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    print('DATA', data)
    assert len(data) == 2
    sections_by_id = {section["id"]: section for section in data}
    assert set(sections_by_id) == {first_section.id, second_section.id}
    assert all(set(section) == ADMIN_SECTION_FIELDS for section in data)
    assert sections_by_id[first_section.id]["order"] == 1
    assert sections_by_id[second_section.id]["order"] == 0


@pytest.mark.asyncio
async def test_update_section_orders_rejects_duplicate_section_ids(
    client,
    admin_headers,
):
    response = await client.patch(
        "/api/sections/admin/order",
        headers=admin_headers,
        json={
            "sections": [
                {"id": 1, "order": 0},
                {"id": 1, "order": 1},
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Duplicate section IDs found"}


@pytest.mark.asyncio
async def test_update_section_orders_rejects_duplicate_order_values(
    client,
    admin_headers,
):
    response = await client.patch(
        "/api/sections/admin/order",
        headers=admin_headers,
        json={
            "sections": [
                {"id": 1, "order": 0},
                {"id": 2, "order": 0},
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Duplicate order values found"}


@pytest.mark.asyncio
async def test_update_section_orders_rejects_sections_from_different_courses(
    client,
    admin_headers,
    section_factory,
):
    first_section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    second_section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )

    response = await client.patch(
        "/api/sections/admin/order",
        headers=admin_headers,
        json={
            "sections": [
                {"id": first_section.id, "order": 0},
                {"id": second_section.id, "order": 1},
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": "All sections must belong to the same course"
    }


@pytest.mark.asyncio
async def test_update_section_orders_rejects_negative_order(
    client,
    admin_headers,
):
    response = await client.patch(
        "/api/sections/admin/order",
        headers=admin_headers,
        json={"sections": [{"id": 1, "order": -1}]},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == [
        "body",
        "sections",
        0,
        "order",
    ]


@pytest.mark.asyncio
async def test_update_section_orders_rejects_non_admin(
    client,
    auth_headers,
):
    response = await client.patch(
        "/api/sections/admin/order",
        headers=auth_headers,
        json={"sections": []},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_update_section_orders_requires_authentication(client):
    response = await client.patch(
        "/api/sections/admin/order",
        json={"sections": []},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


# POST /api/sections/{section_id}/admin/lessons


@pytest.mark.asyncio
async def test_create_lesson_admin_success(
    client,
    admin_headers,
    section_factory,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )

    response = await client.post(
        f"/api/sections/{section.id}/admin/lessons",
        headers=admin_headers,
        json={
            "title": "Python variables",
            "description": "Introduction to Python variables",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert set(data) == ADMIN_LESSON_FIELDS
    assert data["id"] is not None
    assert data["section_id"] == section.id
    assert data["title"] == "Python variables"
    assert data["description"] == "Introduction to Python variables"
    assert data["order"] == 0
    assert data["created_at"]
    assert data["updated_at"]


@pytest.mark.asyncio
async def test_create_lesson_admin_appends_after_existing_lesson(
    client,
    admin_headers,
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    await create_lesson(db, section_id=section.id, order=3)

    response = await client.post(
        f"/api/sections/{section.id}/admin/lessons",
        headers=admin_headers,
        json={"title": "Next lesson"},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["description"] is None
    assert response.json()["order"] == 4


@pytest.mark.asyncio
async def test_create_lesson_admin_section_not_found(client, admin_headers):
    response = await client.post(
        "/api/sections/999999/admin/lessons",
        headers=admin_headers,
        json={"title": "Test lesson"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Section not found"}


@pytest.mark.asyncio
async def test_create_lesson_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )

    response = await client.post(
        f"/api/sections/{section.id}/admin/lessons",
        headers=auth_headers,
        json={"title": "Test lesson"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_create_lesson_admin_requires_authentication(
    client,
    section_factory,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )

    response = await client.post(
        f"/api/sections/{section.id}/admin/lessons",
        json={"title": "Test lesson"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"title": "ab"},
        {"title": "Test lesson", "description": "short"},
    ],
)
async def test_create_lesson_admin_validates_payload(
    client,
    admin_headers,
    section_factory,
    payload,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )

    response = await client.post(
        f"/api/sections/{section.id}/admin/lessons",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# GET /api/sections/{section_id}/lessons


@pytest.mark.asyncio
async def test_get_lessons_returns_public_lessons_in_order(
    client,
    section_factory,
    db,
    auth_headers,
):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    other_section = await section_factory(
        course_id=section.course_id,
        is_published=True,
        order=1,
    )
    second = await create_lesson(
        db,
        section_id=section.id,
        title="Second lesson",
        order=1,
    )
    first = await create_lesson(
        db,
        section_id=section.id,
        title="First lesson",
        order=0,
    )
    await create_lesson(db, section_id=other_section.id, order=0)
    await enroll_in_course(client, auth_headers, section.course_id)

    response = await client.get(
        f"/api/sections/{section.id}/lessons",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert [lesson["id"] for lesson in data] == [first.id, second.id]
    assert all(set(lesson) == PUBLIC_LESSON_FIELDS for lesson in data)
    assert [lesson["order"] for lesson in data] == [0, 1]


@pytest.mark.asyncio
async def test_get_lessons_returns_empty_list(
    client,
    section_factory,
    auth_headers,
):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    await enroll_in_course(client, auth_headers, section.course_id)

    response = await client.get(
        f"/api/sections/{section.id}/lessons",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_lessons_requires_enrollment(
    client,
    section_factory,
    auth_headers,
):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )

    response = await client.get(
        f"/api/sections/{section.id}/lessons",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Enrollment required"}


@pytest.mark.asyncio
async def test_get_lessons_hides_draft_course(
    client,
    section_factory,
    db,
    auth_headers,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    await create_lesson(db, section_id=section.id)

    response = await client.get(
        f"/api/sections/{section.id}/lessons",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_lessons_section_not_found(client, auth_headers):
    response = await client.get(
        "/api/sections/999999/lessons",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Section not found"}


@pytest.mark.asyncio
async def test_get_lessons_rejects_invalid_section_id(client, auth_headers):
    response = await client.get(
        "/api/sections/not-an-id/lessons",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "section_id"]


# GET /api/sections/{section_id}/admin/lessons


@pytest.mark.asyncio
async def test_get_lessons_admin_returns_draft_lessons_in_order(
    client,
    admin_headers,
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    second = await create_lesson(
        db,
        section_id=section.id,
        title="Second lesson",
        order=1,
    )
    first = await create_lesson(
        db,
        section_id=section.id,
        title="First lesson",
        order=0,
    )

    response = await client.get(
        f"/api/sections/{section.id}/admin/lessons",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert [lesson["id"] for lesson in data] == [first.id, second.id]
    assert all(set(lesson) == ADMIN_LESSON_FIELDS for lesson in data)
    assert all(lesson["created_at"] for lesson in data)
    assert all(lesson["updated_at"] for lesson in data)


@pytest.mark.asyncio
async def test_get_lessons_admin_section_not_found(client, admin_headers):
    response = await client.get(
        "/api/sections/999999/admin/lessons",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Section not found"}


@pytest.mark.asyncio
async def test_get_lessons_admin_rejects_non_admin(
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
        f"/api/sections/{section.id}/admin/lessons",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_get_lessons_admin_requires_authentication(
    client,
    section_factory,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )

    response = await client.get(
        f"/api/sections/{section.id}/admin/lessons",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
