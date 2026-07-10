import pytest
from fastapi import status
from sqlalchemy import select

from app.enums import SubmissionStatus
from app.main import app
from app.models import Lesson, Step, Submission, Task, User


SUBMISSION_DETAIL_FIELDS = {
    "id",
    "task_id",
    "source_code",
    "status",
    "submitted_at",
}

SUBMISSION_LIST_FIELDS = {
    "id",
    "task_id",
    "status",
    "submitted_at",
}


async def get_user_by_email(db, email: str) -> User:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalars().one()


async def create_user(db, *, email: str = "other@example.com") -> User:
    user = User(
        email=email,
        password_hash="hashed-password",
        first_name="Other",
        last_name="User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_step(db, section_factory, *, is_published: bool = True) -> Step:
    section = await section_factory(
        course_id=None,
        is_published=is_published,
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


async def create_submission(
    db,
    task_id: int,
    *,
    user_id: int,
    source_code: str = "print('ok')",
    status_: SubmissionStatus = SubmissionStatus.PENDING,
) -> Submission:
    submission = Submission(
        task_id=task_id,
        user_id=user_id,
        source_code=source_code,
        status=status_,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


def create_submission_url() -> str:
    return str(app.url_path_for("create_submission"))


def get_my_submission_url(submission_id: int | str) -> str:
    return str(app.url_path_for("get_my_submission", submission_id=submission_id))


def get_submission_admin_url(submission_id: int | str) -> str:
    return str(app.url_path_for("get_submission_admin", submission_id=submission_id))


def get_my_task_submissions_url(task_id: int | str) -> str:
    return str(app.url_path_for("get_my_task_submissions", task_id=task_id))


def get_user_task_submissions_admin_url(
    task_id: int | str,
    user_id: int | str,
) -> str:
    return str(
        app.url_path_for(
            "get_user_task_submissions_admin",
            task_id=task_id,
            user_id=user_id,
        )
    )


def assert_submission_detail(data: dict, submission: Submission) -> None:
    assert set(data) == SUBMISSION_DETAIL_FIELDS
    assert data["id"] == submission.id
    assert data["task_id"] == submission.task_id
    assert data["source_code"] == submission.source_code
    assert data["status"] == submission.status.value
    assert data["submitted_at"] is not None


def assert_submission_list_item(data: dict, submission: Submission) -> None:
    assert set(data) == SUBMISSION_LIST_FIELDS
    assert data["id"] == submission.id
    assert data["task_id"] == submission.task_id
    assert data["status"] == submission.status.value
    assert data["submitted_at"] is not None


# POST /api/submissions


def test_create_submission_uses_expected_url():
    assert create_submission_url() == "/api/submissions"


@pytest.mark.asyncio
async def test_create_submission_success(
    client,
    auth_headers,
    user_data,
    section_factory,
    db,
):
    user = await get_user_by_email(db, user_data["email"])
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)

    response = await client.post(
        create_submission_url(),
        headers=auth_headers,
        json={
            "task_id": task.id,
            "source_code": "print('ok')",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert set(data) == SUBMISSION_DETAIL_FIELDS
    assert data["task_id"] == task.id
    assert data["source_code"] == "print('ok')"
    assert data["status"] == SubmissionStatus.PENDING.value
    stored_submission = await db.get(Submission, data["id"])
    assert stored_submission is not None
    assert stored_submission.user_id == user.id


@pytest.mark.asyncio
async def test_create_submission_requires_authentication(
    client,
    section_factory,
    db,
):
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)

    response = await client.post(
        create_submission_url(),
        json={
            "task_id": task.id,
            "source_code": "print('ok')",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_create_submission_hides_unpublished_task(
    client,
    auth_headers,
    section_factory,
    db,
):
    step = await create_step(db, section_factory, is_published=False)
    task = await create_task(db, step.id)

    response = await client.post(
        create_submission_url(),
        headers=auth_headers,
        json={
            "task_id": task.id,
            "source_code": "print('ok')",
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload, loc",
    [
        ({"task_id": 0, "source_code": "print('ok')"}, ["body", "task_id"]),
        ({"task_id": 1, "source_code": "x"}, ["body", "source_code"]),
    ],
)
async def test_create_submission_validates_payload(
    client,
    auth_headers,
    payload,
    loc,
):
    response = await client.post(
        create_submission_url(),
        headers=auth_headers,
        json=payload,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == loc


# GET /api/submissions/{submission_id}


def test_get_my_submission_uses_expected_url():
    assert get_my_submission_url(1) == "/api/submissions/1"


@pytest.mark.asyncio
async def test_get_my_submission_success(
    client,
    auth_headers,
    user_data,
    section_factory,
    db,
):
    user = await get_user_by_email(db, user_data["email"])
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    submission = await create_submission(db, task.id, user_id=user.id)

    response = await client.get(
        get_my_submission_url(submission.id),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert_submission_detail(response.json(), submission)


@pytest.mark.asyncio
async def test_get_my_submission_rejects_other_user(
    client,
    auth_headers,
    section_factory,
    db,
):
    other_user = await create_user(db)
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    submission = await create_submission(db, task.id, user_id=other_user.id)

    response = await client.get(
        get_my_submission_url(submission.id),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Access denied"}


@pytest.mark.asyncio
async def test_get_my_submission_not_found(client, auth_headers):
    response = await client.get(
        get_my_submission_url(999999),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Submission not found"}


@pytest.mark.asyncio
async def test_get_my_submission_requires_authentication(client):
    response = await client.get(get_my_submission_url(1))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_get_my_submission_rejects_invalid_id(client, auth_headers):
    response = await client.get(
        get_my_submission_url("not-an-id"),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "submission_id"]


# GET /api/submissions/{submission_id}/admin


def test_get_submission_admin_uses_expected_url():
    assert get_submission_admin_url(1) == "/api/submissions/1/admin"


@pytest.mark.asyncio
async def test_get_submission_admin_success(
    client,
    admin_headers,
    section_factory,
    db,
):
    other_user = await create_user(db)
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    submission = await create_submission(db, task.id, user_id=other_user.id)

    response = await client.get(
        get_submission_admin_url(submission.id),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert_submission_detail(response.json(), submission)


@pytest.mark.asyncio
async def test_get_submission_admin_rejects_non_admin(
    client,
    auth_headers,
    user_data,
    section_factory,
    db,
):
    user = await get_user_by_email(db, user_data["email"])
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    submission = await create_submission(db, task.id, user_id=user.id)

    response = await client.get(
        get_submission_admin_url(submission.id),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }


# GET /api/tasks/{task_id}/submissions


def test_get_my_task_submissions_uses_expected_url():
    assert get_my_task_submissions_url(1) == "/api/tasks/1/submissions"


@pytest.mark.asyncio
async def test_get_my_task_submissions_success(
    client,
    auth_headers,
    user_data,
    section_factory,
    db,
):
    user = await get_user_by_email(db, user_data["email"])
    other_user = await create_user(db)
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    first_submission = await create_submission(
        db,
        task.id,
        user_id=user.id,
        source_code="print('first')",
    )
    second_submission = await create_submission(
        db,
        task.id,
        user_id=user.id,
        source_code="print('second')",
    )
    await create_submission(db, task.id, user_id=other_user.id)

    response = await client.get(
        get_my_task_submissions_url(task.id),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert [submission["id"] for submission in data] == [
        first_submission.id,
        second_submission.id,
    ]
    assert_submission_list_item(data[0], first_submission)
    assert_submission_list_item(data[1], second_submission)


@pytest.mark.asyncio
async def test_get_my_task_submissions_task_not_found(client, auth_headers):
    response = await client.get(
        get_my_task_submissions_url(999999),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.asyncio
async def test_get_my_task_submissions_requires_authentication(client):
    response = await client.get(get_my_task_submissions_url(1))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


# GET /api/tasks/{task_id}/{user_id}/submissions


def test_get_user_task_submissions_admin_uses_expected_url():
    assert (
        get_user_task_submissions_admin_url(1, 2)
        == "/api/tasks/1/2/submissions"
    )


@pytest.mark.asyncio
async def test_get_user_task_submissions_admin_success(
    client,
    admin_headers,
    section_factory,
    db,
):
    other_user = await create_user(db)
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    submission = await create_submission(db, task.id, user_id=other_user.id)

    response = await client.get(
        get_user_task_submissions_admin_url(task.id, other_user.id),
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert_submission_list_item(data[0], submission)


@pytest.mark.asyncio
async def test_get_user_task_submissions_admin_rejects_non_admin(
    client,
    auth_headers,
):
    response = await client.get(
        get_user_task_submissions_admin_url(1, 2),
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }
