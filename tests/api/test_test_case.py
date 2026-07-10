import pytest
from fastapi import status

from app.main import app
from app.models import Lesson, Step, Task, TestCase as DbTestCase


TEST_CASE_FIELDS = {
    "id",
    "task_id",
    "input",
    "expected_output",
    "is_hidden",
    "order",
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
        starter_code="print('hello')",
        time_limit_ms=1000,
        memory_limit_mb=128,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def create_test_case(
    db,
    task_id: int,
    *,
    input_value: str | None = "1 2",
    expected_output: str = "3",
    is_hidden: bool = True,
    order: int = 1,
) -> DbTestCase:
    test_case = DbTestCase(
        task_id=task_id,
        input=input_value,
        expected_output=expected_output,
        is_hidden=is_hidden,
        order=order,
    )
    db.add(test_case)
    await db.commit()
    await db.refresh(test_case)
    return test_case


def assert_test_case_response(data: dict, test_case: DbTestCase) -> None:
    assert set(data) == TEST_CASE_FIELDS
    assert data["id"] == test_case.id
    assert data["task_id"] == test_case.task_id
    assert data["input"] == test_case.input
    assert data["expected_output"] == test_case.expected_output
    assert data["is_hidden"] == test_case.is_hidden
    assert data["order"] == test_case.order


def create_test_case_url() -> str:
    return str(app.url_path_for("create_test_case"))


def get_test_cases_url(task_id: int | str) -> str:
    return str(app.url_path_for("get_test_cases", task_id=task_id))


def update_test_case_url(test_case_id: int | str) -> str:
    return str(app.url_path_for("update_test_case", test_case_id=test_case_id))


def delete_test_case_url(test_case_id: int | str) -> str:
    return str(app.url_path_for("delete_test_case", test_case_id=test_case_id))


# POST /api/test-cases


def test_create_test_case_uses_expected_url():
    assert create_test_case_url() == "/api/test-cases"


@pytest.mark.asyncio
async def test_create_test_case_success(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.post(
        create_test_case_url(),
        headers=admin_headers,
        json={
            "task_id": task.id,
            "input": "1 2",
            "expected_output": "3",
            "is_hidden": False,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert set(data) == TEST_CASE_FIELDS
    assert data["task_id"] == task.id
    assert data["input"] == "1 2"
    assert data["expected_output"] == "3"
    assert data["is_hidden"] is False
    assert data["order"] == 1
    assert await db.get(DbTestCase, data["id"]) is not None


@pytest.mark.asyncio
async def test_create_test_case_task_not_found(client, admin_headers):
    response = await client.post(
        create_test_case_url(),
        headers=admin_headers,
        json={
            "task_id": 999999,
            "input": "1 2",
            "expected_output": "3",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.asyncio
async def test_create_test_case_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.post(
        create_test_case_url(),
        headers=auth_headers,
        json={
            "task_id": task.id,
            "input": "1 2",
            "expected_output": "3",
        },
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_create_test_case_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.post(
        create_test_case_url(),
        json={
            "task_id": task.id,
            "input": "1 2",
            "expected_output": "3",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, loc",
    [
        ({"task_id": 1, "input": "", "expected_output": "3"}, ["body", "input"]),
        ({"task_id": 1, "input": "1 2", "expected_output": ""}, ["body", "expected_output"]),
    ],
)
async def test_create_test_case_validates_payload(
    client,
    admin_headers,
    payload,
    loc,
):
    response = await client.post(
        create_test_case_url(),
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == loc


# GET /api/test-cases/admin/by-task/{task_id}


def test_get_test_cases_uses_expected_url():
    assert get_test_cases_url(1) == "/api/test-cases/admin/by-task/1"


@pytest.mark.asyncio
async def test_get_test_cases_success(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    second = await create_test_case(
        db,
        task.id,
        input_value="second",
        expected_output="2",
        order=2,
    )
    first = await create_test_case(
        db,
        task.id,
        input_value="first",
        expected_output="1",
        order=1,
    )

    response = await client.get(
        get_test_cases_url(task.id),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert [test_case["id"] for test_case in data] == [first.id, second.id]
    assert_test_case_response(data[0], first)
    assert_test_case_response(data[1], second)


@pytest.mark.asyncio
async def test_get_test_cases_task_not_found(client, admin_headers):
    response = await client.get(
        get_test_cases_url(999999),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.asyncio
async def test_get_test_cases_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.get(
        get_test_cases_url(task.id),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


@pytest.mark.asyncio
async def test_get_test_cases_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    response = await client.get(get_test_cases_url(task.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_get_test_cases_rejects_invalid_id(client, admin_headers):
    response = await client.get(
        get_test_cases_url("not-an-id"),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "task_id"]


# PATCH /api/test-cases/admin/{test_case_id}


def test_update_test_case_uses_expected_url():
    assert update_test_case_url(1) == "/api/test-cases/admin/1"


@pytest.mark.asyncio
async def test_update_test_case_updates_expected_output(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    test_case = await create_test_case(
        db,
        task.id,
        input_value="1 2",
        expected_output="3",
        is_hidden=True,
    )

    response = await client.patch(
        update_test_case_url(test_case.id),
        headers=admin_headers,
        json={"expected_output": "4"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_case.id
    assert data["input"] == "1 2"
    assert data["expected_output"] == "4"
    assert data["is_hidden"] is True
    await db.refresh(test_case)
    assert test_case.expected_output == "4"


@pytest.mark.asyncio
async def test_update_test_case_updates_visibility(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    test_case = await create_test_case(db, task.id, is_hidden=True)

    response = await client.patch(
        update_test_case_url(test_case.id),
        headers=admin_headers,
        json={"is_hidden": False},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_hidden"] is False
    await db.refresh(test_case)
    assert test_case.is_hidden is False


@pytest.mark.asyncio
async def test_update_test_case_not_found(client, admin_headers):
    response = await client.patch(
        update_test_case_url(999999),
        headers=admin_headers,
        json={"expected_output": "4"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Test Case not found"}


@pytest.mark.asyncio
async def test_update_test_case_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    test_case = await create_test_case(db, task.id)
    original_expected_output = test_case.expected_output

    response = await client.patch(
        update_test_case_url(test_case.id),
        headers=auth_headers,
        json={"expected_output": "4"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }
    await db.refresh(test_case)
    assert test_case.expected_output == original_expected_output


@pytest.mark.asyncio
async def test_update_test_case_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    test_case = await create_test_case(db, task.id)

    response = await client.patch(
        update_test_case_url(test_case.id),
        json={"expected_output": "4"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, loc",
    [
        ({"input": ""}, ["body", "input"]),
        ({"expected_output": ""}, ["body", "expected_output"]),
    ],
)
async def test_update_test_case_validates_payload(
    client,
    admin_headers,
    section_factory,
    db,
    payload,
    loc,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    test_case = await create_test_case(db, task.id)

    response = await client.patch(
        update_test_case_url(test_case.id),
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == loc


@pytest.mark.asyncio
async def test_update_test_case_rejects_invalid_id(client, admin_headers):
    response = await client.patch(
        update_test_case_url("not-an-id"),
        headers=admin_headers,
        json={"expected_output": "4"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "test_case_id"]


# DELETE /api/test-cases/admin/{test_case_id}


def test_delete_test_case_uses_expected_url():
    assert delete_test_case_url(1) == "/api/test-cases/admin/1"


@pytest.mark.asyncio
async def test_delete_test_case_success(
    client,
    admin_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    test_case = await create_test_case(db, task.id)
    test_case_id = test_case.id

    response = await client.delete(
        delete_test_case_url(test_case_id),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert await db.get(DbTestCase, test_case_id) is None


@pytest.mark.asyncio
async def test_delete_test_case_not_found(client, admin_headers):
    response = await client.delete(
        delete_test_case_url(999999),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Test Case not found"}


@pytest.mark.asyncio
async def test_delete_test_case_rejects_non_admin(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    test_case = await create_test_case(db, task.id)

    response = await client.delete(
        delete_test_case_url(test_case.id),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }
    assert await db.get(DbTestCase, test_case.id) is not None


@pytest.mark.asyncio
async def test_delete_test_case_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    test_case = await create_test_case(db, task.id)

    response = await client.delete(delete_test_case_url(test_case.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
    assert await db.get(DbTestCase, test_case.id) is not None


@pytest.mark.asyncio
async def test_delete_test_case_rejects_invalid_id(client, admin_headers):
    response = await client.delete(
        delete_test_case_url("not-an-id"),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "test_case_id"]
