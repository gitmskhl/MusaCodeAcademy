import pytest
from fastapi import status
from sqlalchemy import select

from app.models import Enrollment, Lesson, Step, StepProgress, User


PROGRESS_FIELDS = {
    "id",
    "user_id",
    "step_id",
    "completed_at",
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


async def create_enrollment(db, *, user_id: int, course_id: int) -> Enrollment:
    enrollment = Enrollment(user_id=user_id, course_id=course_id)
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def create_lesson(db, *, section_id: int) -> Lesson:
    lesson = Lesson(
        section_id=section_id,
        title="Variables",
        description="Learn variables",
        order=0,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def create_step(db, *, lesson_id: int) -> Step:
    step = Step(
        lesson_id=lesson_id,
        title="First step",
        order=0,
        content={"layout": "single", "blocks": []},
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def create_step_target(
    db,
    section_factory,
    *,
    is_published: bool = True,
):
    section = await section_factory(
        course_id=None,
        is_published=is_published,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_step(db, lesson_id=lesson.id)
    return section.course_id, step


@pytest.mark.asyncio
async def test_complete_step_success(
    client,
    auth_headers,
    course_factory,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course_id, step = await create_step_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)

    response = await client.post(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert set(data) == PROGRESS_FIELDS
    assert data["user_id"] == user.id
    assert data["step_id"] == step.id
    assert data["completed_at"]


@pytest.mark.asyncio
async def test_complete_step_requires_authentication(client, section_factory, db):
    _, step = await create_step_target(db, section_factory)

    response = await client.post(f"/api/progress/steps/{step.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_complete_step_rejects_user_without_enrollment(
    client,
    auth_headers,
    section_factory,
    db,
):
    _, step = await create_step_target(db, section_factory)

    response = await client.post(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {"detail": "Enrollment not found"}


@pytest.mark.asyncio
async def test_complete_step_rejects_draft_course(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course_id, step = await create_step_target(
        db,
        section_factory,
        is_published=False,
    )
    await create_enrollment(db, user_id=user.id, course_id=course_id)

    response = await client.post(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Course not found"}


@pytest.mark.asyncio
async def test_get_step_progress_returns_completed_status(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course_id, step = await create_step_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)
    await client.post(f"/api/progress/steps/{step.id}", headers=auth_headers)

    response = await client.get(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"completed": True}


@pytest.mark.asyncio
async def test_get_step_progress_is_scoped_to_current_user(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    current_user = await get_user_by_email(db, user_data["email"])
    other_user = await create_user(db)
    course_id, step = await create_step_target(db, section_factory)
    await create_enrollment(db, user_id=current_user.id, course_id=course_id)
    await create_enrollment(db, user_id=other_user.id, course_id=course_id)
    db.add(StepProgress(user_id=other_user.id, step_id=step.id))
    await db.commit()

    response = await client.get(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"completed": False}


@pytest.mark.asyncio
async def test_uncomplete_step_deletes_progress(
    client,
    auth_headers,
    section_factory,
    db,
    user_data,
):
    user = await get_user_by_email(db, user_data["email"])
    course_id, step = await create_step_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)
    response = await client.post(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )
    progress_id = response.json()["id"]

    response = await client.delete(
        f"/api/progress/steps/{step.id}",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert await db.get(StepProgress, progress_id) is None


@pytest.mark.asyncio
async def test_uncomplete_step_requires_authentication(client, section_factory, db):
    _, step = await create_step_target(db, section_factory)

    response = await client.delete(f"/api/progress/steps/{step.id}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
