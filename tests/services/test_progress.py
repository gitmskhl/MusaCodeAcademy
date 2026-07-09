import pytest
from fastapi import HTTPException, status

from app.models import Enrollment, Lesson, Step, StepProgress, User
from app.services import progress as service_progress


async def create_user(db, *, email: str = "student@example.com") -> User:
    user = User(
        email=email,
        password_hash="hashed-password",
        first_name="Student",
        last_name="User",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


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


async def create_enrollment(db, *, user_id: int, course_id: int) -> Enrollment:
    enrollment = Enrollment(user_id=user_id, course_id=course_id)
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def create_progress_target(
    db,
    section_factory,
    *,
    is_published: bool = True,
):
    user = await create_user(db)
    section = await section_factory(
        course_id=None,
        is_published=is_published,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_step(db, lesson_id=lesson.id)
    return user, section.course_id, step


@pytest.mark.asyncio
async def test_complete_step_creates_progress(section_factory, db):
    user, course_id, step = await create_progress_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)

    progress = await service_progress.complete_step(
        step_id=step.id,
        user_id=user.id,
        db=db,
    )

    assert progress.id is not None
    assert progress.user_id == user.id
    assert progress.step_id == step.id
    assert progress.completed_at is not None


@pytest.mark.asyncio
async def test_complete_step_returns_existing_progress(section_factory, db):
    user, course_id, step = await create_progress_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)
    first = await service_progress.complete_step(
        step_id=step.id,
        user_id=user.id,
        db=db,
    )

    second = await service_progress.complete_step(
        step_id=step.id,
        user_id=user.id,
        db=db,
    )

    assert second.id == first.id


@pytest.mark.asyncio
async def test_complete_step_rejects_missing_step(db):
    user = await create_user(db)

    with pytest.raises(HTTPException) as exc:
        await service_progress.complete_step(
            step_id=999_999,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Step not found"


@pytest.mark.asyncio
async def test_complete_step_rejects_draft_course(section_factory, db):
    user, course_id, step = await create_progress_target(
        db,
        section_factory,
        is_published=False,
    )
    await create_enrollment(db, user_id=user.id, course_id=course_id)

    with pytest.raises(HTTPException) as exc:
        await service_progress.complete_step(
            step_id=step.id,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_complete_step_rejects_user_without_enrollment(section_factory, db):
    user, _, step = await create_progress_target(db, section_factory)

    with pytest.raises(HTTPException) as exc:
        await service_progress.complete_step(
            step_id=step.id,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Enrollment not found"


@pytest.mark.asyncio
async def test_uncomplete_step_deletes_progress(section_factory, db):
    user, course_id, step = await create_progress_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)
    progress = await service_progress.complete_step(
        step_id=step.id,
        user_id=user.id,
        db=db,
    )

    await service_progress.uncomplete_step(
        step_id=step.id,
        user_id=user.id,
        db=db,
    )

    assert await db.get(StepProgress, progress.id) is None


@pytest.mark.asyncio
async def test_uncomplete_step_ignores_missing_progress(section_factory, db):
    user, course_id, step = await create_progress_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)

    await service_progress.uncomplete_step(
        step_id=step.id,
        user_id=user.id,
        db=db,
    )

    completed = await service_progress.is_step_completed(
        step_id=step.id,
        user_id=user.id,
        db=db,
    )
    assert completed is False


@pytest.mark.asyncio
async def test_is_step_completed_returns_true_for_completed_step(
    section_factory,
    db,
):
    user, course_id, step = await create_progress_target(db, section_factory)
    await create_enrollment(db, user_id=user.id, course_id=course_id)
    await service_progress.complete_step(
        step_id=step.id,
        user_id=user.id,
        db=db,
    )

    completed = await service_progress.is_step_completed(
        step_id=step.id,
        user_id=user.id,
        db=db,
    )

    assert completed is True
