import pytest
from fastapi import status

from app.models import Lesson


ADMIN_LESSON_FIELDS = {
    "id",
    "section_id",
    "title",
    "description",
    "order",
    "created_at",
    "updated_at",
}


async def create_lesson(
    db,
    *,
    section_id: int,
    title: str = "Test lesson",
    description: str | None = "Detailed lesson description",
    order: int = 0,
) -> Lesson:
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
async def test_update_lesson_orders_admin_success(
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
    first_lesson = await create_lesson(
        db,
        section_id=section.id,
        title="First lesson",
        order=0,
    )
    second_lesson = await create_lesson(
        db,
        section_id=section.id,
        title="Second lesson",
        order=1,
    )

    response = await client.patch(
        "/api/lessons/admin/order",
        headers=admin_headers,
        json={
            "lessons": [
                {"id": first_lesson.id, "order": 1},
                {"id": second_lesson.id, "order": 0},
            ]
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    lessons_by_id = {lesson["id"]: lesson for lesson in data}
    assert set(lessons_by_id) == {first_lesson.id, second_lesson.id}
    assert all(set(lesson) == ADMIN_LESSON_FIELDS for lesson in data)
    assert lessons_by_id[first_lesson.id]["order"] == 1
    assert lessons_by_id[second_lesson.id]["order"] == 0
    assert (await db.get(Lesson, first_lesson.id)).order == 1
    assert (await db.get(Lesson, second_lesson.id)).order == 0


@pytest.mark.asyncio
async def test_update_lesson_orders_rejects_duplicate_lesson_ids(
    client,
    admin_headers,
):
    response = await client.patch(
        "/api/lessons/admin/order",
        headers=admin_headers,
        json={
            "lessons": [
                {"id": 1, "order": 0},
                {"id": 1, "order": 1},
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Duplicate lesson IDs found"}


@pytest.mark.asyncio
async def test_update_lesson_orders_rejects_duplicate_order_values(
    client,
    admin_headers,
):
    response = await client.patch(
        "/api/lessons/admin/order",
        headers=admin_headers,
        json={
            "lessons": [
                {"id": 1, "order": 0},
                {"id": 2, "order": 0},
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Duplicate order values found"}


@pytest.mark.asyncio
async def test_update_lesson_orders_rejects_lessons_from_different_sections(
    client,
    admin_headers,
    section_factory,
    db,
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
    first_lesson = await create_lesson(
        db,
        section_id=first_section.id,
        order=0,
    )
    second_lesson = await create_lesson(
        db,
        section_id=second_section.id,
        order=0,
    )

    response = await client.patch(
        "/api/lessons/admin/order",
        headers=admin_headers,
        json={
            "lessons": [
                {"id": first_lesson.id, "order": 0},
                {"id": second_lesson.id, "order": 1},
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": "All lessons must belong to the same section"
    }


@pytest.mark.asyncio
async def test_update_lesson_orders_rejects_negative_order(
    client,
    admin_headers,
):
    response = await client.patch(
        "/api/lessons/admin/order",
        headers=admin_headers,
        json={"lessons": [{"id": 1, "order": -1}]},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == [
        "body",
        "lessons",
        0,
        "order",
    ]


@pytest.mark.asyncio
async def test_update_lesson_orders_rejects_non_admin(
    client,
    auth_headers,
):
    response = await client.patch(
        "/api/lessons/admin/order",
        headers=auth_headers,
        json={"lessons": []},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_update_lesson_orders_requires_authentication(client):
    response = await client.patch(
        "/api/lessons/admin/order",
        json={"lessons": []},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
