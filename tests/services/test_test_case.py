from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models import Lesson, Step, Task, TestCase as DbTestCase
from app.schemas.testCase import (
    TestCaseCreate as CreateTestCaseSchema,
    TestCaseUpdate as UpdateTestCaseSchema,
)
from app.services import testCase as service_test_case


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


@pytest.mark.asyncio
async def test_create_test_case_assigns_first_order(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    test_case = await service_test_case.create_test_case(
        testInfo=CreateTestCaseSchema(
            task_id=task.id,
            input="1 2",
            expected_output="3",
            is_hidden=False,
        ),
        db=db,
    )

    assert test_case.id is not None
    assert test_case.task_id == task.id
    assert test_case.input == "1 2"
    assert test_case.expected_output == "3"
    assert test_case.is_hidden is False
    assert test_case.order == 1


@pytest.mark.asyncio
async def test_create_test_case_increments_order_per_task(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    await create_test_case(db, task.id, order=1)

    test_case = await service_test_case.create_test_case(
        testInfo=CreateTestCaseSchema(
            task_id=task.id,
            input="4 5",
            expected_output="9",
        ),
        db=db,
    )

    assert test_case.order == 2


@pytest.mark.asyncio
async def test_create_test_case_task_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_test_case.create_test_case(
            testInfo=CreateTestCaseSchema(
                task_id=999_999,
                input="1 2",
                expected_output="3",
            ),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Task not found"


@pytest.mark.asyncio
async def test_get_test_cases_by_task_returns_ordered_cases(section_factory, db):
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

    result = await service_test_case.get_test_cases_by_task(
        task_id=task.id,
        db=db,
    )

    assert [test_case.id for test_case in result] == [first.id, second.id]


@pytest.mark.asyncio
async def test_get_test_cases_by_task_task_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_test_case.get_test_cases_by_task(
            task_id=999_999,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Task not found"


@pytest.mark.asyncio
async def test_update_test_case_updates_only_provided_fields(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    test_case = await create_test_case(
        db,
        task.id,
        input_value="1 2",
        expected_output="3",
        is_hidden=True,
        order=1,
    )

    updated_test_case = await service_test_case.update_test_case(
        test_case_id=test_case.id,
        test_case_update=UpdateTestCaseSchema(expected_output="4"),
        db=db,
    )

    assert updated_test_case.id == test_case.id
    assert updated_test_case.input == "1 2"
    assert updated_test_case.expected_output == "4"
    assert updated_test_case.is_hidden is True
    assert updated_test_case.order == 1
    assert (await db.get(DbTestCase, test_case.id)).expected_output == "4"


@pytest.mark.asyncio
async def test_update_test_case_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_test_case.update_test_case(
            test_case_id=999_999,
            test_case_update=UpdateTestCaseSchema(expected_output="4"),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Test Case not found"


@pytest.mark.asyncio
async def test_delete_test_case_removes_case(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    test_case = await create_test_case(db, task.id)
    test_case_id = test_case.id

    await service_test_case.delete_test_case(
        test_case_id=test_case_id,
        db=db,
    )

    assert await db.get(DbTestCase, test_case_id) is None


@pytest.mark.asyncio
async def test_delete_test_case_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_test_case.delete_test_case(
            test_case_id=999_999,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Test Case not found"


@pytest.mark.asyncio
async def test_create_test_case_rolls_back_on_commit_error(
    section_factory,
    db,
    monkeypatch,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(IntegrityError):
        await service_test_case.create_test_case(
            testInfo=CreateTestCaseSchema(
                task_id=task.id,
                input="1 2",
                expected_output="3",
            ),
            db=db,
        )

    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()
