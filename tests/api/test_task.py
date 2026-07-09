import pytest
from fastapi import status

from app.main import app
from app.models import Lesson, Step, Task


TASK_FIELDS = {
    "id",
    "step_id",
    "title",
    "description",
    "time_limit_ms",
    "memory_limit_mb",
}


async def create_step(db, section_factory) -> Step:
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = Lesson(
        section_id=section.id,
        title="Test lesson",
        description="Test lesson description",
        order=0,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)

    step = Step(
        lesson_id=lesson.id,
        title="Test step",
        order=0,
        content={
            "version": 1,
            "layout": "vertical",
            "blocks": [],
        },
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def create_task(db, step_id: int) -> Task:
    task = Task(
        step_id=step_id,
        title="Practice task",
        description="Solve this practice task",
        time_limit_ms=1000,
        memory_limit_mb=128,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


def assert_task_response(data: dict, task: Task) -> None:
    assert set(data) == TASK_FIELDS
    assert data["id"] == task.id
    assert data["step_id"] == task.step_id
    assert data["title"] == task.title
    assert data["description"] == task.description
    assert data["time_limit_ms"] == task.time_limit_ms
    assert data["memory_limit_mb"] == task.memory_limit_mb


def delete_task_url(task_id: int | str) -> str:
    return str(app.url_path_for("delete_task", task_id=task_id))


def update_task_url(task_id: int | str) -> str:
    return str(app.url_path_for("update_task", task_id=task_id))


# GET /api/tasks/admin/{task_id}


@pytest.mark.asyncio
async def test_get_task_admin_success(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.get(
        f"/api/tasks/admin/{task.id}",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert_task_response(response.json(), task)


@pytest.mark.asyncio
async def test_get_task_admin_not_found(client, admin_headers):
    response = await client.get(
        "/api/tasks/admin/999999",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.asyncio
async def test_get_task_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.get(
        f"/api/tasks/admin/{task.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_get_task_admin_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.get(f"/api/tasks/admin/{task.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_get_task_admin_rejects_invalid_id(client, admin_headers):
    response = await client.get(
        "/api/tasks/admin/not-an-id",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "task_id"]


# GET /api/tasks/admin/by-step/{step_id}


@pytest.mark.asyncio
async def test_get_task_by_step_admin_success(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.get(
        f"/api/tasks/admin/by-step/{step.id}",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert_task_response(response.json(), task)


@pytest.mark.asyncio
async def test_get_task_by_step_admin_step_not_found(client, admin_headers):
    response = await client.get(
        "/api/tasks/admin/by-step/999999",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Step not found"}


@pytest.mark.asyncio
async def test_get_task_by_step_admin_task_not_found(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)

    response = await client.get(
        f"/api/tasks/admin/by-step/{step.id}",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.asyncio
async def test_get_task_by_step_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)

    response = await client.get(
        f"/api/tasks/admin/by-step/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_get_task_by_step_admin_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)

    response = await client.get(f"/api/tasks/admin/by-step/{step.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_get_task_by_step_admin_rejects_invalid_id(
    client,
    admin_headers,
):
    response = await client.get(
        "/api/tasks/admin/by-step/not-an-id",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "step_id"]


# DELETE /api/tasks/admin/{task_id}


def test_delete_task_admin_uses_expected_url():
    assert delete_task_url(1) == "/api/tasks/admin/1"


@pytest.mark.asyncio
async def test_delete_task_admin_success(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    task_id = task.id

    response = await client.delete(
        delete_task_url(task_id),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert await db.get(Task, task_id) is None


@pytest.mark.asyncio
async def test_delete_task_admin_not_found(client, admin_headers):
    response = await client.delete(
        delete_task_url(999999),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.asyncio
async def test_delete_task_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.delete(
        delete_task_url(task.id),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }
    assert await db.get(Task, task.id) is not None


@pytest.mark.asyncio
async def test_delete_task_admin_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.delete(delete_task_url(task.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
    assert await db.get(Task, task.id) is not None


@pytest.mark.asyncio
async def test_delete_task_admin_rejects_invalid_id(client, admin_headers):
    response = await client.delete(
        delete_task_url("not-an-id"),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "task_id"]


# PATCH /api/tasks/admin/{task_id}


def test_update_task_admin_uses_expected_url():
    assert update_task_url(1) == "/api/tasks/admin/1"


@pytest.mark.asyncio
async def test_update_task_admin_updates_only_title(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.patch(
        update_task_url(task.id),
        headers=admin_headers,
        json={"title": "Updated task"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert set(data) == TASK_FIELDS
    assert data["id"] == task.id
    assert data["step_id"] == task.step_id
    assert data["title"] == "Updated task"
    assert data["description"] == task.description
    assert data["time_limit_ms"] == task.time_limit_ms
    assert data["memory_limit_mb"] == task.memory_limit_mb
    await db.refresh(task)
    assert task.title == "Updated task"


@pytest.mark.asyncio
async def test_update_task_admin_updates_limits(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.patch(
        update_task_url(task.id),
        headers=admin_headers,
        json={
            "description": "Solve this updated practice task",
            "time_limit_ms": 2000,
            "memory_limit_mb": 256,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["title"] == task.title
    assert data["description"] == "Solve this updated practice task"
    assert data["time_limit_ms"] == 2000
    assert data["memory_limit_mb"] == 256
    await db.refresh(task)
    assert task.description == "Solve this updated practice task"
    assert task.time_limit_ms == 2000
    assert task.memory_limit_mb == 256


@pytest.mark.asyncio
async def test_update_task_admin_not_found(client, admin_headers):
    response = await client.patch(
        update_task_url(999999),
        headers=admin_headers,
        json={"title": "Updated task"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.asyncio
async def test_update_task_admin_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    original_title = task.title

    response = await client.patch(
        update_task_url(task.id),
        headers=auth_headers,
        json={"title": "Updated task"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }
    await db.refresh(task)
    assert task.title == original_title


@pytest.mark.asyncio
async def test_update_task_admin_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.patch(
        update_task_url(task.id),
        json={"title": "Updated task"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, loc",
    [
        ({"title": ""}, ["body", "title"]),
        ({"description": "too short"}, ["body", "description"]),
        ({"time_limit_ms": 0}, ["body", "time_limit_ms"]),
        ({"time_limit_ms": 30001}, ["body", "time_limit_ms"]),
        ({"memory_limit_mb": 0}, ["body", "memory_limit_mb"]),
        ({"memory_limit_mb": 1025}, ["body", "memory_limit_mb"]),
    ],
)
async def test_update_task_admin_validates_payload(
    client,
    admin_headers,
    section_factory,
    db,
    payload,
    loc,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.patch(
        update_task_url(task.id),
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == loc


@pytest.mark.asyncio
async def test_update_task_admin_rejects_invalid_id(client, admin_headers):
    response = await client.patch(
        update_task_url("not-an-id"),
        headers=admin_headers,
        json={"title": "Updated task"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "task_id"]
