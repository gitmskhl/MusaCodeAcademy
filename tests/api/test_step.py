import pytest
from fastapi import status

from app.main import app
from app.models import Lesson, Step


STEP_FIELDS = {
    "id",
    "lesson_id",
    "title",
    "order",
    "content",
}

VERTICAL_CONTENT = {
    "version": 1,
    "layout": "vertical",
    "blocks": [
        {
            "type": "text",
            "data": {"text": "A variable stores a value."},
        },
    ],
}

TWO_COLUMNS_CONTENT = {
    "version": 1,
    "layout": "two_columns",
    "left": [
        {
            "type": "text",
            "data": {"text": "Left column"},
        },
    ],
    "right": [
        {
            "type": "image",
            "data": {
                "file_id": 1,
                "width": 100,
                "caption": None,
            },
        },
    ],
}

CODE_CONTENT = {
    "version": 1,
    "layout": "vertical",
    "blocks": [
        {
            "type": "code",
            "data": {
                "language": "python",
                "code": "print('Hello, world!')",
            },
        },
    ],
}


async def create_lesson(db, *, section_id: int) -> Lesson:
    lesson = Lesson(
        section_id=section_id,
        title="Test lesson",
        description="Test lesson description",
        order=0,
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
        content=content or VERTICAL_CONTENT,
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def create_step_for_course(
    db,
    section_factory,
    *,
    is_published: bool,
) -> Step:
    section = await section_factory(
        course_id=None,
        is_published=is_published,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    return await create_step(db, lesson_id=lesson.id)


def assert_step_response(data: dict, step: Step) -> None:
    assert set(data) == STEP_FIELDS
    assert data["id"] == step.id
    assert data["lesson_id"] == step.lesson_id
    assert data["title"] == step.title
    assert data["order"] == step.order
    assert data["content"] == step.content


def delete_step_url(step_id: int | str) -> str:
    return str(app.url_path_for("delete_step", step_id=step_id))


# GET /api/steps/{step_id}


@pytest.mark.asyncio
async def test_get_step_success(client, section_factory, db):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=True,
    )

    response = await client.get(f"/api/steps/{step.id}")

    assert response.status_code == status.HTTP_200_OK
    assert_step_response(response.json(), step)


@pytest.mark.asyncio
async def test_get_step_hides_step_from_draft_course(
    client,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=False,
    )

    response = await client.get(f"/api/steps/{step.id}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_step_not_found(client):
    response = await client.get("/api/steps/999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Step not found"}


@pytest.mark.asyncio
async def test_get_step_rejects_invalid_id(client):
    response = await client.get("/api/steps/not-an-id")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "step_id"]


# GET /api/steps/{step_id}/admin


@pytest.mark.asyncio
async def test_get_step_admin_returns_draft(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=False,
    )

    response = await client.get(
        f"/api/steps/{step.id}/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert_step_response(response.json(), step)


@pytest.mark.asyncio
async def test_get_step_admin_not_found(client, admin_headers):
    response = await client.get(
        "/api/steps/999999/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Step not found"}


@pytest.mark.asyncio
async def test_get_step_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=True,
    )

    response = await client.get(
        f"/api/steps/{step.id}/admin",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_get_step_admin_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=True,
    )

    response = await client.get(f"/api/steps/{step.id}/admin")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_get_step_admin_rejects_invalid_id(client, admin_headers):
    response = await client.get(
        "/api/steps/not-an-id/admin",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "step_id"]


# DELETE /api/steps/{step_id}/admin


def test_delete_step_admin_uses_expected_url():
    assert delete_step_url(1) == "/api/steps/1/admin"


@pytest.mark.asyncio
async def test_delete_step_admin_success(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=False,
    )
    step_id = step.id

    response = await client.delete(
        delete_step_url(step_id),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert await db.get(Step, step_id) is None


@pytest.mark.asyncio
async def test_delete_step_admin_not_found(client, admin_headers):
    response = await client.delete(
        delete_step_url(999999),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Step not found"}


@pytest.mark.asyncio
async def test_delete_step_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=True,
    )

    response = await client.delete(
        delete_step_url(step.id),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }
    assert await db.get(Step, step.id) is not None


@pytest.mark.asyncio
async def test_delete_step_admin_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=True,
    )

    response = await client.delete(delete_step_url(step.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
    assert await db.get(Step, step.id) is not None


@pytest.mark.asyncio
async def test_delete_step_admin_rejects_invalid_id(client, admin_headers):
    response = await client.delete(
        delete_step_url("not-an-id"),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "step_id"]


# PATCH /api/steps/{step_id}/admin


@pytest.mark.asyncio
async def test_update_step_admin_updates_only_title(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=False,
    )
    original_content = step.content

    response = await client.patch(
        f"/api/steps/{step.id}/admin",
        headers=admin_headers,
        json={"title": "Updated step"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert set(data) == STEP_FIELDS
    assert data["id"] == step.id
    assert data["lesson_id"] == step.lesson_id
    assert data["title"] == "Updated step"
    assert data["order"] == step.order
    assert data["content"] == original_content
    await db.refresh(step)
    assert step.title == "Updated step"
    assert step.content == original_content


@pytest.mark.asyncio
async def test_update_step_admin_updates_content(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=False,
    )
    original_title = step.title

    response = await client.patch(
        f"/api/steps/{step.id}/admin",
        headers=admin_headers,
        json={"content": TWO_COLUMNS_CONTENT},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == original_title
    assert data["content"] == TWO_COLUMNS_CONTENT
    await db.refresh(step)
    assert step.title == original_title
    assert step.content == TWO_COLUMNS_CONTENT


@pytest.mark.asyncio
async def test_update_step_admin_updates_content_with_code_block(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=False,
    )

    response = await client.patch(
        f"/api/steps/{step.id}/admin",
        headers=admin_headers,
        json={"content": CODE_CONTENT},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["content"] == CODE_CONTENT
    await db.refresh(step)
    assert step.content == CODE_CONTENT


@pytest.mark.asyncio
async def test_update_step_admin_not_found(client, admin_headers):
    response = await client.patch(
        "/api/steps/999999/admin",
        headers=admin_headers,
        json={"title": "Updated step"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Step not found"}


@pytest.mark.asyncio
async def test_update_step_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=True,
    )
    original_title = step.title

    response = await client.patch(
        f"/api/steps/{step.id}/admin",
        headers=auth_headers,
        json={"title": "Updated step"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }
    await db.refresh(step)
    assert step.title == original_title


@pytest.mark.asyncio
async def test_update_step_admin_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=True,
    )

    response = await client.patch(
        f"/api/steps/{step.id}/admin",
        json={"title": "Updated step"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"title": ""},
        {
            "content": {
                "version": 1,
                "layout": "unknown",
                "blocks": [],
            }
        },
        {
            "content": {
                "version": 1,
                "layout": "vertical",
                "blocks": [
                    {
                        "type": "image",
                        "data": {"width": 100},
                    }
                ],
            }
        },
        {
            "content": {
                "version": 1,
                "layout": "vertical",
                "blocks": [
                    {
                        "type": "image",
                        "data": {"file_id": 0, "width": 100},
                    }
                ],
            }
        },
        {
            "content": {
                "version": 1,
                "layout": "vertical",
                "blocks": [
                    {
                        "type": "image",
                        "data": {"file_id": 1, "width": 9},
                    }
                ],
            }
        },
        {
            "content": {
                "version": 1,
                "layout": "vertical",
                "blocks": [
                    {
                        "type": "image",
                        "data": {"file_id": 1, "width": 101},
                    }
                ],
            }
        },
        {
            "content": {
                "version": 1,
                "layout": "vertical",
                "blocks": [
                    {
                        "type": "code",
                        "data": {"code": "print('missing language')"},
                    }
                ],
            }
        },
        {
            "content": {
                "version": 1,
                "layout": "vertical",
                "blocks": [
                    {
                        "type": "code",
                        "data": {
                            "language": "javascript",
                            "code": "console.log('unsupported')",
                        },
                    }
                ],
            }
        },
        {
            "content": {
                "version": 1,
                "layout": "vertical",
                "blocks": [
                    {
                        "type": "code",
                        "data": {"language": "python", "code": ""},
                    }
                ],
            }
        },
    ],
)
async def test_update_step_admin_validates_payload(
    client,
    admin_headers,
    section_factory,
    db,
    payload,
):
    step = await create_step_for_course(
        db,
        section_factory,
        is_published=False,
    )

    response = await client.patch(
        f"/api/steps/{step.id}/admin",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"][0] == "body"


@pytest.mark.asyncio
async def test_update_step_admin_rejects_invalid_id(client, admin_headers):
    response = await client.patch(
        "/api/steps/not-an-id/admin",
        headers=admin_headers,
        json={"title": "Updated step"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "step_id"]


# PATCH /api/steps/admin/order


@pytest.mark.asyncio
async def test_update_steps_order_admin_success(
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
    first_step = await create_step(
        db,
        lesson_id=lesson.id,
        title="First step",
        order=0,
    )
    second_step = await create_step(
        db,
        lesson_id=lesson.id,
        title="Second step",
        order=1,
    )

    response = await client.patch(
        "/api/steps/admin/order",
        headers=admin_headers,
        json={
            "steps": [
                {"id": first_step.id, "order": 1},
                {"id": second_step.id, "order": 0},
            ]
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    steps_by_id = {step["id"]: step for step in data}
    assert set(steps_by_id) == {first_step.id, second_step.id}
    assert all(set(step) == STEP_FIELDS for step in data)
    assert steps_by_id[first_step.id]["order"] == 1
    assert steps_by_id[second_step.id]["order"] == 0
    assert (await db.get(Step, first_step.id)).order == 1
    assert (await db.get(Step, second_step.id)).order == 0


@pytest.mark.asyncio
async def test_update_steps_order_rejects_duplicate_step_ids(
    client,
    admin_headers,
):
    response = await client.patch(
        "/api/steps/admin/order",
        headers=admin_headers,
        json={
            "steps": [
                {"id": 1, "order": 0},
                {"id": 1, "order": 1},
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Duplicate step IDs found"}


@pytest.mark.asyncio
async def test_update_steps_order_rejects_duplicate_order_values(
    client,
    admin_headers,
):
    response = await client.patch(
        "/api/steps/admin/order",
        headers=admin_headers,
        json={
            "steps": [
                {"id": 1, "order": 0},
                {"id": 2, "order": 0},
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Duplicate order values found"}


@pytest.mark.asyncio
async def test_update_steps_order_rejects_steps_from_different_lessons(
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
    first_lesson = await create_lesson(db, section_id=section.id)
    second_lesson = await create_lesson(db, section_id=section.id)
    first_step = await create_step(
        db,
        lesson_id=first_lesson.id,
        order=0,
    )
    second_step = await create_step(
        db,
        lesson_id=second_lesson.id,
        order=0,
    )

    response = await client.patch(
        "/api/steps/admin/order",
        headers=admin_headers,
        json={
            "steps": [
                {"id": first_step.id, "order": 0},
                {"id": second_step.id, "order": 1},
            ]
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": "All steps must belong to the same lesson"
    }


@pytest.mark.asyncio
async def test_update_steps_order_rejects_negative_order(
    client,
    admin_headers,
):
    response = await client.patch(
        "/api/steps/admin/order",
        headers=admin_headers,
        json={"steps": [{"id": 1, "order": -1}]},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == [
        "body",
        "steps",
        0,
        "order",
    ]


@pytest.mark.asyncio
async def test_update_steps_order_rejects_non_admin(
    client,
    auth_headers,
):
    response = await client.patch(
        "/api/steps/admin/order",
        headers=auth_headers,
        json={"steps": []},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_update_steps_order_requires_authentication(client):
    response = await client.patch(
        "/api/steps/admin/order",
        json={"steps": []},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
