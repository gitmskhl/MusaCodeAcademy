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


async def create_step(
    db,
    *,
    lesson_id: int,
    title: str = "First step",
    order: int = 0,
) -> Step:
    step = Step(
        lesson_id=lesson_id,
        title=title,
        order=order,
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
    return user, section.course_id, lesson, step


@pytest.mark.asyncio
async def test_complete_step_creates_progress(section_factory, db):
    user, course_id, _, step = await create_progress_target(db, section_factory)
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
    user, course_id, _, step = await create_progress_target(db, section_factory)
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
    user, course_id, _, step = await create_progress_target(
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
    user, _, _, step = await create_progress_target(db, section_factory)

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
    user, course_id, _, step = await create_progress_target(db, section_factory)
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
    user, course_id, _, step = await create_progress_target(db, section_factory)
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
    user, course_id, _, step = await create_progress_target(db, section_factory)
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


@pytest.mark.asyncio
async def test_get_lesson_progress_returns_completed_steps_in_lesson_order(
    section_factory,
    db,
):
    user, course_id, lesson, first_step = await create_progress_target(
        db,
        section_factory,
    )
    second_step = await create_step(
        db,
        lesson_id=lesson.id,
        title="Second step",
        order=1,
    )
    third_step = await create_step(
        db,
        lesson_id=lesson.id,
        title="Third step",
        order=2,
    )
    await create_enrollment(db, user_id=user.id, course_id=course_id)
    await service_progress.complete_step(
        step_id=third_step.id,
        user_id=user.id,
        db=db,
    )
    await service_progress.complete_step(
        step_id=first_step.id,
        user_id=user.id,
        db=db,
    )

    progress = await service_progress.get_lesson_progress(
        lesson_id=lesson.id,
        user_id=user.id,
        db=db,
    )

    assert progress.lesson_id == lesson.id
    assert progress.completed_step_ids == [first_step.id, third_step.id]
    assert progress.completed_count == 2
    assert progress.total_count == 3
    assert progress.percent == 67


@pytest.mark.asyncio
async def test_get_lesson_progress_returns_zero_for_empty_lesson(
    section_factory,
    db,
):
    user = await create_user(db)
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    await create_enrollment(db, user_id=user.id, course_id=section.course_id)

    progress = await service_progress.get_lesson_progress(
        lesson_id=lesson.id,
        user_id=user.id,
        db=db,
    )

    assert progress.lesson_id == lesson.id
    assert progress.completed_step_ids == []
    assert progress.completed_count == 0
    assert progress.total_count == 0
    assert progress.percent == 0


@pytest.mark.asyncio
async def test_get_lesson_progress_ignores_other_users_progress(
    section_factory,
    db,
):
    user, course_id, lesson, step = await create_progress_target(
        db,
        section_factory,
    )
    other_user = await create_user(db, email="other@example.com")
    await create_enrollment(db, user_id=user.id, course_id=course_id)
    await create_enrollment(db, user_id=other_user.id, course_id=course_id)
    await service_progress.complete_step(
        step_id=step.id,
        user_id=other_user.id,
        db=db,
    )

    progress = await service_progress.get_lesson_progress(
        lesson_id=lesson.id,
        user_id=user.id,
        db=db,
    )

    assert progress.completed_step_ids == []
    assert progress.completed_count == 0
    assert progress.total_count == 1
    assert progress.percent == 0


@pytest.mark.asyncio
async def test_get_lesson_progress_rejects_missing_lesson(db):
    user = await create_user(db)

    with pytest.raises(HTTPException) as exc:
        await service_progress.get_lesson_progress(
            lesson_id=999_999,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Lesson not found"


@pytest.mark.asyncio
async def test_get_lesson_progress_rejects_draft_course(section_factory, db):
    user, course_id, lesson, _ = await create_progress_target(
        db,
        section_factory,
        is_published=False,
    )
    await create_enrollment(db, user_id=user.id, course_id=course_id)

    with pytest.raises(HTTPException) as exc:
        await service_progress.get_lesson_progress(
            lesson_id=lesson.id,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_lesson_progress_rejects_user_without_enrollment(
    section_factory,
    db,
):
    user, _, lesson, _ = await create_progress_target(db, section_factory)

    with pytest.raises(HTTPException) as exc:
        await service_progress.get_lesson_progress(
            lesson_id=lesson.id,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Enrollment not found"


@pytest.mark.asyncio
async def test_get_course_sections_progress_returns_section_stats(
    section_factory,
    db,
):
    user = await create_user(db)
    first_section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    second_section = await section_factory(
        course_id=first_section.course_id,
        is_published=True,
        order=1,
    )
    first_lesson = await create_lesson(db, section_id=first_section.id)
    second_lesson = await create_lesson(db, section_id=first_section.id)
    first_step = await create_step(
        db,
        lesson_id=first_lesson.id,
        title="First lesson step 1",
        order=0,
    )
    second_step = await create_step(
        db,
        lesson_id=first_lesson.id,
        title="First lesson step 2",
        order=1,
    )
    third_step = await create_step(
        db,
        lesson_id=second_lesson.id,
        title="Second lesson step 1",
        order=0,
    )
    await create_step(
        db,
        lesson_id=second_lesson.id,
        title="Second lesson step 2",
        order=1,
    )
    await create_enrollment(
        db,
        user_id=user.id,
        course_id=first_section.course_id,
    )
    for step in [first_step, second_step, third_step]:
        await service_progress.complete_step(
            step_id=step.id,
            user_id=user.id,
            db=db,
        )

    progress = await service_progress.get_course_sections_progress(
        course_id=first_section.course_id,
        user_id=user.id,
        db=db,
    )

    assert progress.course_id == first_section.course_id
    assert [section.section_id for section in progress.sections] == [
        first_section.id,
        second_section.id,
    ]
    assert progress.sections[0].completed_step_count == 3
    assert progress.sections[0].total_step_count == 4
    assert progress.sections[0].completed_lesson_count == 1
    assert progress.sections[0].total_lesson_count == 2
    assert progress.sections[0].percent == 75
    assert progress.sections[1].completed_step_count == 0
    assert progress.sections[1].total_step_count == 0
    assert progress.sections[1].completed_lesson_count == 0
    assert progress.sections[1].total_lesson_count == 0
    assert progress.sections[1].percent == 0


@pytest.mark.asyncio
async def test_get_course_sections_progress_ignores_other_users_progress(
    section_factory,
    db,
):
    user = await create_user(db)
    other_user = await create_user(db, email="other@example.com")
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_step(db, lesson_id=lesson.id)
    await create_enrollment(db, user_id=user.id, course_id=section.course_id)
    await create_enrollment(
        db,
        user_id=other_user.id,
        course_id=section.course_id,
    )
    await service_progress.complete_step(
        step_id=step.id,
        user_id=other_user.id,
        db=db,
    )

    progress = await service_progress.get_course_sections_progress(
        course_id=section.course_id,
        user_id=user.id,
        db=db,
    )

    assert len(progress.sections) == 1
    assert progress.sections[0].section_id == section.id
    assert progress.sections[0].completed_step_count == 0
    assert progress.sections[0].total_step_count == 1
    assert progress.sections[0].completed_lesson_count == 0
    assert progress.sections[0].total_lesson_count == 1
    assert progress.sections[0].percent == 0


@pytest.mark.asyncio
async def test_get_course_sections_progress_returns_empty_for_course_without_sections(
    course_factory,
    db,
):
    user = await create_user(db)
    course = await course_factory(slug="empty-course", is_published=True)
    await create_enrollment(db, user_id=user.id, course_id=course.id)

    progress = await service_progress.get_course_sections_progress(
        course_id=course.id,
        user_id=user.id,
        db=db,
    )

    assert progress.course_id == course.id
    assert progress.sections == []


@pytest.mark.asyncio
async def test_get_course_sections_progress_rejects_missing_course(db):
    user = await create_user(db)

    with pytest.raises(HTTPException) as exc:
        await service_progress.get_course_sections_progress(
            course_id=999_999,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_course_sections_progress_rejects_draft_course(
    course_factory,
    db,
):
    user = await create_user(db)
    course = await course_factory(slug="draft-course", is_published=False)
    await create_enrollment(db, user_id=user.id, course_id=course.id)

    with pytest.raises(HTTPException) as exc:
        await service_progress.get_course_sections_progress(
            course_id=course.id,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_course_sections_progress_rejects_user_without_enrollment(
    course_factory,
    db,
):
    user = await create_user(db)
    course = await course_factory(slug="published-course", is_published=True)

    with pytest.raises(HTTPException) as exc:
        await service_progress.get_course_sections_progress(
            course_id=course.id,
            user_id=user.id,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Enrollment not found"


@pytest.mark.asyncio
async def test_get_my_courses_progress_returns_enrolled_published_courses(
    section_factory,
    db,
):
    user = await create_user(db)
    first_section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    second_section = await section_factory(
        course_id=first_section.course_id,
        is_published=True,
        order=1,
    )
    second_course_section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    first_lesson = await create_lesson(db, section_id=first_section.id)
    second_lesson = await create_lesson(db, section_id=second_section.id)
    second_course_lesson = await create_lesson(
        db,
        section_id=second_course_section.id,
    )
    first_step = await create_step(db, lesson_id=first_lesson.id, order=0)
    second_step = await create_step(db, lesson_id=first_lesson.id, order=1)
    third_step = await create_step(db, lesson_id=second_lesson.id, order=0)
    second_course_step = await create_step(
        db,
        lesson_id=second_course_lesson.id,
        order=0,
    )
    await create_enrollment(
        db,
        user_id=user.id,
        course_id=first_section.course_id,
    )
    await create_enrollment(
        db,
        user_id=user.id,
        course_id=second_course_section.course_id,
    )
    for step in [first_step, second_step, second_course_step]:
        await service_progress.complete_step(
            step_id=step.id,
            user_id=user.id,
            db=db,
        )

    progress = await service_progress.get_my_courses_progress(
        user_id=user.id,
        db=db,
    )

    progress_by_course = {item.course_id: item for item in progress}
    assert set(progress_by_course) == {
        first_section.course_id,
        second_course_section.course_id,
    }
    first_course_progress = progress_by_course[first_section.course_id]
    assert first_course_progress.completed_step_count == 2
    assert first_course_progress.total_step_count == 3
    assert first_course_progress.completed_lesson_count == 1
    assert first_course_progress.total_lesson_count == 2
    assert first_course_progress.completed_section_count == 1
    assert first_course_progress.total_section_count == 2
    assert first_course_progress.percent == 67

    second_course_progress = progress_by_course[second_course_section.course_id]
    assert second_course_progress.completed_step_count == 1
    assert second_course_progress.total_step_count == 1
    assert second_course_progress.completed_lesson_count == 1
    assert second_course_progress.total_lesson_count == 1
    assert second_course_progress.completed_section_count == 1
    assert second_course_progress.total_section_count == 1
    assert second_course_progress.percent == 100
    assert third_step.id is not None


@pytest.mark.asyncio
async def test_get_my_courses_progress_ignores_draft_and_unenrolled_courses(
    course_factory,
    db,
):
    user = await create_user(db)
    published = await course_factory(slug="published", is_published=True)
    draft = await course_factory(slug="draft", is_published=False)
    await course_factory(slug="not-enrolled", is_published=True)
    await create_enrollment(db, user_id=user.id, course_id=published.id)
    await create_enrollment(db, user_id=user.id, course_id=draft.id)

    progress = await service_progress.get_my_courses_progress(
        user_id=user.id,
        db=db,
    )

    assert [item.course_id for item in progress] == [published.id]
    assert progress[0].percent == 0
    assert progress[0].total_step_count == 0


@pytest.mark.asyncio
async def test_get_my_courses_progress_ignores_other_users_progress(
    section_factory,
    db,
):
    user = await create_user(db)
    other_user = await create_user(db, email="other@example.com")
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_step(db, lesson_id=lesson.id)
    await create_enrollment(db, user_id=user.id, course_id=section.course_id)
    await create_enrollment(
        db,
        user_id=other_user.id,
        course_id=section.course_id,
    )
    await service_progress.complete_step(
        step_id=step.id,
        user_id=other_user.id,
        db=db,
    )

    progress = await service_progress.get_my_courses_progress(
        user_id=user.id,
        db=db,
    )

    assert len(progress) == 1
    assert progress[0].course_id == section.course_id
    assert progress[0].completed_step_count == 0
    assert progress[0].total_step_count == 1
    assert progress[0].percent == 0


@pytest.mark.asyncio
async def test_get_my_courses_progress_returns_empty_when_no_enrollments(db):
    user = await create_user(db)

    progress = await service_progress.get_my_courses_progress(
        user_id=user.id,
        db=db,
    )

    assert progress == []
