from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models import Lesson, Step, Task
from app.schemas.task import TaskUpdate
from app.services import task as service_task


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


@pytest.mark.asyncio
async def test_update_task_updates_only_provided_fields(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    updated_task = await service_task.update_task(
        task_id=task.id,
        taskUpdate=TaskUpdate(title="Updated task"),
        db=db,
    )

    assert updated_task.id == task.id
    assert updated_task.step_id == step.id
    assert updated_task.title == "Updated task"
    assert updated_task.description == "Solve this practice task"
    assert updated_task.time_limit_ms == 1000
    assert updated_task.memory_limit_mb == 128
    assert (await db.get(Task, task.id)).title == "Updated task"


@pytest.mark.asyncio
async def test_update_task_updates_limits(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    updated_task = await service_task.update_task(
        task_id=task.id,
        taskUpdate=TaskUpdate(
            description="Solve this updated practice task",
            time_limit_ms=2000,
            memory_limit_mb=256,
        ),
        db=db,
    )

    assert updated_task.title == "Practice task"
    assert updated_task.description == "Solve this updated practice task"
    assert updated_task.time_limit_ms == 2000
    assert updated_task.memory_limit_mb == 256
    stored_task = await db.get(Task, task.id)
    assert stored_task.description == "Solve this updated practice task"
    assert stored_task.time_limit_ms == 2000
    assert stored_task.memory_limit_mb == 256


@pytest.mark.asyncio
async def test_update_task_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_task.update_task(
            task_id=999_999,
            taskUpdate=TaskUpdate(title="Updated task"),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Task not found"


@pytest.mark.asyncio
async def test_update_task_not_found_after_step_cascade_delete(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    await db.delete(step)
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await service_task.update_task(
            task_id=task.id,
            taskUpdate=TaskUpdate(title="Updated task"),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Task not found"


@pytest.mark.asyncio
async def test_update_task_integrity_error(section_factory, db, monkeypatch):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_task.update_task(
            task_id=task.id,
            taskUpdate=TaskUpdate(title="Updated task"),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == "Task already exists for this step"
    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()
