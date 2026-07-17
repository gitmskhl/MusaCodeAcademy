import pytest
from fastapi import status

from app.models import Lesson, Step


ADMIN_LESSON_FIELDS = {
    "id",
    "section_id",
    "title",
    "description",
    "order",
    "created_at",
    "updated_at",
}

STEP_FIELDS = {
    "id",
    "lesson_id",
    "title",
    "order",
    "content",
}

STEP_CONTENT = {
    "version": 1,
    "layout": "vertical",
    "blocks": [
        {
            "type": "text",
            "data": {"text": "A variable stores a value."},
        },
    ],
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


async def create_step(
    db,
    *,
    lesson_id: int,
    title: str = "Test step",
    order: int = 0,
    content: dict | None = None,
) -> Step:
    step = Step(
        lesson_id=lesson_id,
        title=title,
        order=order,
        content=content or STEP_CONTENT,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


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


# POST /api/lessons/{lesson_id}/steps/admin


@pytest.mark.asyncio
async def test_create_step_admin_success(
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
    lesson = await create_lesson(db, section_id=section.id)

    response = await client.post(
        f"/api/lessons/{lesson.id}/steps/admin",
        headers=admin_headers,
        json={"title": "Python variables", "content": STEP_CONTENT},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert set(data) == STEP_FIELDS
    assert data["lesson_id"] == lesson.id
    assert data["title"] == "Python variables"
    assert data["order"] == 0
    assert data["content"] == STEP_CONTENT
    step = await db.get(Step, data["id"])
    assert step is not None
    assert step.lesson_id == lesson.id


@pytest.mark.asyncio
async def test_create_step_admin_appends_after_existing_step(
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
    lesson = await create_lesson(db, section_id=section.id)
    await create_step(db, lesson_id=lesson.id, order=3)

    response = await client.post(
        f"/api/lessons/{lesson.id}/steps/admin",
        headers=admin_headers,
        json={"title": "Next step", "content": STEP_CONTENT},
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["order"] == 4


@pytest.mark.asyncio
async def test_create_step_admin_lesson_not_found(client, admin_headers):
    response = await client.post(
        "/api/lessons/999999/steps/admin",
        headers=admin_headers,
        json={"title": "Test step", "content": STEP_CONTENT},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Lesson not found"}


@pytest.mark.asyncio
async def test_create_step_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)

    response = await client.post(
        f"/api/lessons/{lesson.id}/steps/admin",
        headers=auth_headers,
        json={"title": "Test step", "content": STEP_CONTENT},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_create_step_admin_requires_authentication(
    client,
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)

    response = await client.post(
        f"/api/lessons/{lesson.id}/steps/admin",
        json={"title": "Test step", "content": STEP_CONTENT},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_create_step_admin_validates_payload(
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
    lesson = await create_lesson(db, section_id=section.id)

    response = await client.post(
        f"/api/lessons/{lesson.id}/steps/admin",
        headers=admin_headers,
        json={"title": "", "content": STEP_CONTENT},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["body", "title"]


# GET /api/lessons/{lesson_id}/steps


@pytest.mark.asyncio
async def test_get_steps_returns_public_steps_in_order(
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
    lesson = await create_lesson(db, section_id=section.id)
    other_lesson = await create_lesson(
        db,
        section_id=section.id,
        title="Other lesson",
        order=1,
    )
    second = await create_step(
        db,
        lesson_id=lesson.id,
        title="Second step",
        order=1,
    )
    first = await create_step(
        db,
        lesson_id=lesson.id,
        title="First step",
        order=0,
    )
    await create_step(db, lesson_id=other_lesson.id, order=0)
    await enroll_in_course(client, auth_headers, section.course_id)

    response = await client.get(
        f"/api/lessons/{lesson.id}/steps",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert [step["id"] for step in data] == [first.id, second.id]
    assert all(set(step) == STEP_FIELDS for step in data)
    assert [step["order"] for step in data] == [0, 1]


@pytest.mark.asyncio
async def test_get_steps_returns_empty_list(
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
    lesson = await create_lesson(db, section_id=section.id)
    await enroll_in_course(client, auth_headers, section.course_id)

    response = await client.get(
        f"/api/lessons/{lesson.id}/steps",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_steps_requires_enrollment(
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
    lesson = await create_lesson(db, section_id=section.id)

    response = await client.get(
        f"/api/lessons/{lesson.id}/steps",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Enrollment required"}


@pytest.mark.asyncio
async def test_get_steps_hides_draft_course(
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
    lesson = await create_lesson(db, section_id=section.id)
    await create_step(db, lesson_id=lesson.id)

    response = await client.get(
        f"/api/lessons/{lesson.id}/steps",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_steps_lesson_not_found(client, auth_headers):
    response = await client.get(
        "/api/lessons/999999/steps",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Lesson not found"}


@pytest.mark.asyncio
async def test_get_steps_rejects_invalid_lesson_id(client, auth_headers):
    response = await client.get(
        "/api/lessons/not-an-id/steps",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "lesson_id"]


# GET /api/lessons/{lesson_id}/steps/admin


@pytest.mark.asyncio
async def test_get_steps_admin_returns_draft_steps_in_order(
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
    lesson = await create_lesson(db, section_id=section.id)
    second = await create_step(
        db,
        lesson_id=lesson.id,
        title="Second step",
        order=1,
    )
    first = await create_step(
        db,
        lesson_id=lesson.id,
        title="First step",
        order=0,
    )

    response = await client.get(
        f"/api/lessons/{lesson.id}/steps/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert [step["id"] for step in data] == [first.id, second.id]
    assert all(set(step) == STEP_FIELDS for step in data)


@pytest.mark.asyncio
async def test_get_steps_admin_lesson_not_found(client, admin_headers):
    response = await client.get(
        "/api/lessons/999999/steps/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Lesson not found"}


@pytest.mark.asyncio
async def test_get_steps_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)

    response = await client.get(
        f"/api/lessons/{lesson.id}/steps/admin",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_get_steps_admin_requires_authentication(
    client,
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)

    response = await client.get(
        f"/api/lessons/{lesson.id}/steps/admin",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
