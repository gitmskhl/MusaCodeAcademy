from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models import Lesson, Step
from app.schemas.steps.step import StepCreate
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
