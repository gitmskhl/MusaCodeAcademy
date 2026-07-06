from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models import Lesson, Step
from app.schemas.steps.step import (
    StepCreate,
    StepOrderUpdate,
    StepOrderUpdateList,
    StepUpdate,
)
from app.services import step as service_step


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


async def create_existing_step(
    db,
    *,
    lesson_id: int,
    order: int,
) -> Step:
    step = Step(
        lesson_id=lesson_id,
        title=f"Existing step {order}",
        order=order,
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


def make_step_info(title: str = "Python variables") -> StepCreate:
    return StepCreate(
        title=title,
        content={
            "version": 1,
            "layout": "vertical",
            "blocks": [
                {
                    "type": "text",
                    "data": {"text": "A variable stores a value."},
                },
            ],
        },
    )


@pytest.mark.asyncio
async def test_create_step_success(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step_info = make_step_info()

    step = await service_step.create_step(
        lesson_id=lesson.id,
        stepInfo=step_info,
        db=db,
    )

    assert step.id is not None
    assert step.lesson_id == lesson.id
    assert step.title == step_info.title
    assert step.order == 0
    assert step.content == step_info.content.model_dump()
    assert await db.get(Step, step.id) is step


@pytest.mark.asyncio
async def test_create_step_uses_next_order_for_lesson(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    other_lesson = Lesson(
        section_id=section.id,
        title="Other lesson",
        description=None,
        order=1,
    )
    db.add(other_lesson)
    await db.commit()
    await db.refresh(other_lesson)
    await create_existing_step(db, lesson_id=lesson.id, order=1)
    await create_existing_step(db, lesson_id=lesson.id, order=4)
    await create_existing_step(db, lesson_id=other_lesson.id, order=20)

    step = await service_step.create_step(
        lesson_id=lesson.id,
        stepInfo=make_step_info("Next step"),
        db=db,
    )

    assert step.order == 5


@pytest.mark.asyncio
async def test_create_step_lesson_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_step.create_step(
            lesson_id=999_999,
            stepInfo=make_step_info(),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Lesson not found"


@pytest.mark.asyncio
async def test_create_step_integrity_error(section_factory, db, monkeypatch):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_step.create_step(
            lesson_id=lesson.id,
            stepInfo=make_step_info(),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == (
        "Failed to create step due to integrity error"
    )
    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_steps_returns_steps_in_order(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    other_lesson = await create_lesson(db, section_id=section.id)
    third = await create_existing_step(db, lesson_id=lesson.id, order=2)
    first = await create_existing_step(db, lesson_id=lesson.id, order=0)
    second = await create_existing_step(db, lesson_id=lesson.id, order=1)
    await create_existing_step(db, lesson_id=other_lesson.id, order=0)

    steps = await service_step.get_steps(
        lesson_id=lesson.id,
        db=db,
        check_course_published=False,
    )

    assert [step.id for step in steps] == [
        first.id,
        second.id,
        third.id,
    ]


@pytest.mark.asyncio
async def test_get_steps_returns_empty_list(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)

    steps = await service_step.get_steps(
        lesson_id=lesson.id,
        db=db,
        check_course_published=False,
    )

    assert steps == []


@pytest.mark.asyncio
async def test_get_steps_lesson_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_step.get_steps(
            lesson_id=999_999,
            db=db,
            check_course_published=False,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Lesson not found"


@pytest.mark.asyncio
async def test_get_steps_section_not_found():
    lesson = SimpleNamespace(section_id=123)
    db = AsyncMock()
    db.get.side_effect = [lesson, None]

    with pytest.raises(HTTPException) as exc:
        await service_step.get_steps(lesson_id=1, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Section not found"


@pytest.mark.asyncio
async def test_get_steps_course_not_found():
    lesson = SimpleNamespace(section_id=123)
    section = SimpleNamespace(course_id=456)
    db = AsyncMock()
    db.get.side_effect = [lesson, section, None]

    with pytest.raises(HTTPException) as exc:
        await service_step.get_steps(lesson_id=1, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_steps_hides_steps_from_draft_course(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    await create_existing_step(db, lesson_id=lesson.id, order=0)

    with pytest.raises(HTTPException) as exc:
        await service_step.get_steps(lesson_id=lesson.id, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_steps_returns_steps_for_published_course(
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)

    steps = await service_step.get_steps(lesson_id=lesson.id, db=db)

    assert [item.id for item in steps] == [step.id]


@pytest.mark.asyncio
async def test_get_steps_returns_draft_when_course_check_disabled(
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)

    steps = await service_step.get_steps(
        lesson_id=lesson.id,
        db=db,
        check_course_published=False,
    )

    assert [item.id for item in steps] == [step.id]


@pytest.mark.asyncio
async def test_get_step_success_for_published_course(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)

    result = await service_step.get_step(step_id=step.id, db=db)

    assert result.id == step.id


@pytest.mark.asyncio
async def test_get_step_returns_draft_when_course_check_disabled(
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)

    result = await service_step.get_step(
        step_id=step.id,
        db=db,
        check_course_published=False,
    )

    assert result.id == step.id


@pytest.mark.asyncio
async def test_get_step_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_step.get_step(
            step_id=999_999,
            db=db,
            check_course_published=False,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Step not found"


@pytest.mark.asyncio
async def test_get_step_lesson_not_found():
    step = SimpleNamespace(lesson_id=123)
    db = AsyncMock()
    db.get.side_effect = [step, None]

    with pytest.raises(HTTPException) as exc:
        await service_step.get_step(step_id=1, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Lesson not found"


@pytest.mark.asyncio
async def test_get_step_section_not_found():
    step = SimpleNamespace(lesson_id=123)
    lesson = SimpleNamespace(section_id=456)
    db = AsyncMock()
    db.get.side_effect = [step, lesson, None]

    with pytest.raises(HTTPException) as exc:
        await service_step.get_step(step_id=1, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Section not found"


@pytest.mark.asyncio
async def test_get_step_course_not_found():
    step = SimpleNamespace(lesson_id=123)
    lesson = SimpleNamespace(section_id=456)
    section = SimpleNamespace(course_id=789)
    db = AsyncMock()
    db.get.side_effect = [step, lesson, section, None]

    with pytest.raises(HTTPException) as exc:
        await service_step.get_step(step_id=1, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_step_hides_step_from_draft_course(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)

    with pytest.raises(HTTPException) as exc:
        await service_step.get_step(step_id=step.id, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_step_viewer_returns_step_and_lesson_navigation(
    course_factory,
    section_factory,
    db,
):
    course = await course_factory(
        slug="python-viewer",
        is_published=True,
    )
    section = await section_factory(
        course_id=course.id,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    other_lesson = await create_lesson(db, section_id=section.id)
    first = await create_existing_step(db, lesson_id=lesson.id, order=2)
    current = await create_existing_step(db, lesson_id=lesson.id, order=7)
    last = await create_existing_step(db, lesson_id=lesson.id, order=12)
    await create_existing_step(db, lesson_id=other_lesson.id, order=0)

    viewer = await service_step.get_step_viewer(
        step_id=current.id,
        course_slug=course.slug,
        db=db,
    )

    assert viewer.step.id == current.id
    assert viewer.step.lesson_id == lesson.id
    assert viewer.step.title == current.title
    assert viewer.step.order == current.order
    assert viewer.step.content.model_dump() == current.content
    assert viewer.navigation.position == 2
    assert viewer.navigation.total == 3
    assert viewer.navigation.previous_step_id == first.id
    assert viewer.navigation.next_step_id == last.id
    assert viewer.lesson.id == lesson.id
    assert viewer.lesson.section_id == section.id
    assert viewer.lesson.title == lesson.title
    assert [step.id for step in viewer.lesson.steps] == [
        first.id,
        current.id,
        last.id,
    ]
    assert [step.title for step in viewer.lesson.steps] == [
        first.title,
        current.title,
        last.title,
    ]


@pytest.mark.asyncio
async def test_get_step_viewer_handles_single_step_lesson(
    course_factory,
    section_factory,
    db,
):
    course = await course_factory(
        slug="single-step-course",
        is_published=True,
    )
    section = await section_factory(
        course_id=course.id,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=9)

    viewer = await service_step.get_step_viewer(
        step_id=step.id,
        course_slug=course.slug,
        db=db,
    )

    assert viewer.navigation.position == 1
    assert viewer.navigation.total == 1
    assert viewer.navigation.previous_step_id is None
    assert viewer.navigation.next_step_id is None


@pytest.mark.asyncio
async def test_get_step_viewer_rejects_wrong_course_slug(
    course_factory,
    section_factory,
    db,
):
    course = await course_factory(
        slug="actual-course",
        is_published=True,
    )
    section = await section_factory(
        course_id=course.id,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)

    with pytest.raises(HTTPException) as exc:
        await service_step.get_step_viewer(
            step_id=step.id,
            course_slug="another-course",
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Step not found"


@pytest.mark.asyncio
async def test_get_step_viewer_hides_step_from_draft_course(
    course_factory,
    section_factory,
    db,
):
    course = await course_factory(
        slug="draft-course",
        is_published=False,
    )
    section = await section_factory(
        course_id=course.id,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)

    with pytest.raises(HTTPException) as exc:
        await service_step.get_step_viewer(
            step_id=step.id,
            course_slug=course.slug,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Step not found"


@pytest.mark.asyncio
async def test_get_first_lesson_step_id_returns_first_ordered_step(
    course_factory,
    section_factory,
    db,
):
    course = await course_factory(
        slug="first-lesson-step",
        is_published=True,
    )
    section = await section_factory(
        course_id=course.id,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    await create_existing_step(db, lesson_id=lesson.id, order=8)
    first = await create_existing_step(db, lesson_id=lesson.id, order=2)

    step_id = await service_step.get_first_lesson_step_id(
        lesson_id=lesson.id,
        course_slug=course.slug,
        db=db,
    )

    assert step_id == first.id


@pytest.mark.asyncio
async def test_get_first_lesson_step_id_rejects_empty_lesson(
    course_factory,
    section_factory,
    db,
):
    course = await course_factory(
        slug="empty-lesson",
        is_published=True,
    )
    section = await section_factory(
        course_id=course.id,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)

    with pytest.raises(HTTPException) as exc:
        await service_step.get_first_lesson_step_id(
            lesson_id=lesson.id,
            course_slug=course.slug,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Lesson step not found"


@pytest.mark.asyncio
async def test_delete_step_success(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)
    step_id = step.id

    await service_step.delete_step(step_id=step_id, db=db)

    assert await db.get(Step, step_id) is None


@pytest.mark.asyncio
async def test_delete_step_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_step.delete_step(step_id=999_999, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Step not found"


@pytest.mark.asyncio
async def test_delete_step_integrity_error(section_factory, db, monkeypatch):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_step.delete_step(step_id=step.id, db=db)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == (
        "Failed to delete step due to integrity error"
    )
    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_step_updates_only_provided_fields(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=3)
    original_content = step.content

    updated_step = await service_step.update_step(
        step_id=step.id,
        stepInfo=StepUpdate(title="Updated step"),
        db=db,
    )

    assert updated_step.id == step.id
    assert updated_step.lesson_id == lesson.id
    assert updated_step.title == "Updated step"
    assert updated_step.order == 3
    assert updated_step.content == original_content
    assert (await db.get(Step, step.id)).title == "Updated step"


@pytest.mark.asyncio
async def test_update_step_updates_content(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)
    original_title = step.title
    update_info = StepUpdate(
        content={
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
                    "type": "text",
                    "data": {"text": "Right column"},
                },
            ],
        },
    )

    updated_step = await service_step.update_step(
        step_id=step.id,
        stepInfo=update_info,
        db=db,
    )

    expected_content = update_info.content.model_dump()
    assert updated_step.title == original_title
    assert updated_step.content == expected_content
    assert (await db.get(Step, step.id)).content == expected_content


@pytest.mark.asyncio
async def test_update_step_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_step.update_step(
            step_id=999_999,
            stepInfo=StepUpdate(title="Updated step"),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Step not found"


@pytest.mark.asyncio
async def test_update_step_rolls_back_on_commit_error(
    section_factory,
    db,
    monkeypatch,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)
    commit_mock = AsyncMock(side_effect=RuntimeError("forced error"))
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_step.update_step(
            step_id=step.id,
            stepInfo=StepUpdate(title="Updated step"),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Failed to update step"
    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_steps_order_success(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    first_step = await create_existing_step(
        db,
        lesson_id=lesson.id,
        order=0,
    )
    second_step = await create_existing_step(
        db,
        lesson_id=lesson.id,
        order=1,
    )
    order_list = StepOrderUpdateList(
        steps=[
            StepOrderUpdate(id=first_step.id, order=1),
            StepOrderUpdate(id=second_step.id, order=0),
        ]
    )

    result = await service_step.update_steps_order(
        order_list=order_list,
        db=db,
    )

    steps_by_id = {step.id: step for step in result}
    assert set(steps_by_id) == {first_step.id, second_step.id}
    assert steps_by_id[first_step.id].order == 1
    assert steps_by_id[second_step.id].order == 0
    assert (await db.get(Step, first_step.id)).order == 1
    assert (await db.get(Step, second_step.id)).order == 0


@pytest.mark.asyncio
async def test_update_steps_order_duplicate_step_ids(db):
    order_list = StepOrderUpdateList(
        steps=[
            StepOrderUpdate(id=1, order=0),
            StepOrderUpdate(id=1, order=1),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await service_step.update_steps_order(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Duplicate step IDs found"


@pytest.mark.asyncio
async def test_update_steps_order_duplicate_order_values(db):
    order_list = StepOrderUpdateList(
        steps=[
            StepOrderUpdate(id=1, order=0),
            StepOrderUpdate(id=2, order=0),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await service_step.update_steps_order(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Duplicate order values found"


@pytest.mark.asyncio
async def test_update_steps_order_steps_from_different_lessons(
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
    first_step = await create_existing_step(
        db,
        lesson_id=first_lesson.id,
        order=0,
    )
    second_step = await create_existing_step(
        db,
        lesson_id=second_lesson.id,
        order=0,
    )
    order_list = StepOrderUpdateList(
        steps=[
            StepOrderUpdate(id=first_step.id, order=0),
            StepOrderUpdate(id=second_step.id, order=1),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await service_step.update_steps_order(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "All steps must belong to the same lesson"


@pytest.mark.asyncio
async def test_update_steps_order_integrity_error(
    section_factory,
    db,
    monkeypatch,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)
    order_list = StepOrderUpdateList(
        steps=[StepOrderUpdate(id=step.id, order=1)]
    )
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_step.update_steps_order(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == (
        "Failed to update step orders due to integrity error"
    )
    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_steps_order_empty_list(db):
    result = await service_step.update_steps_order(
        order_list=StepOrderUpdateList(steps=[]),
        db=db,
    )

    assert result == []


@pytest.mark.asyncio
async def test_update_steps_order_ignores_unknown_step_id(
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    step = await create_existing_step(db, lesson_id=lesson.id, order=0)
    unknown_step_id = step.id + 999_999
    order_list = StepOrderUpdateList(
        steps=[
            StepOrderUpdate(id=step.id, order=1),
            StepOrderUpdate(id=unknown_step_id, order=2),
        ]
    )

    result = await service_step.update_steps_order(
        order_list=order_list,
        db=db,
    )

    assert [item.id for item in result] == [step.id]
    assert (await db.get(Step, step.id)).order == 1
    assert await db.get(Step, unknown_step_id) is None
