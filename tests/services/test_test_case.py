from unittest.mock import AsyncMock
from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Lesson, Step, Task, TestCase as DbTestCase
from app.schemas.testCase import (
    TestCaseCreate as CreateTestCaseSchema,
    TestCaseUpdate as UpdateTestCaseSchema,
)
from app.services import testCase as service_test_case


def create_zip(files: list[tuple[str, bytes | str]]) -> BytesIO:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for filename, content in files:
            archive.writestr(filename, content)
    buffer.seek(0)
    return buffer


def upload_file(
    files: list[tuple[str, bytes | str]],
    *,
    filename: str = "tests.zip",
) -> UploadFile:
    return UploadFile(filename=filename, file=create_zip(files))


async def get_test_cases_for_task(db, task_id: int) -> list[DbTestCase]:
    result = await db.execute(
        select(DbTestCase)
        .where(DbTestCase.task_id == task_id)
        .order_by(DbTestCase.order)
    )
    return list(result.scalars().all())


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


@pytest.mark.asyncio
async def test_import_tests_zip_creates_ordered_hidden_test_cases(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    archive = upload_file([
        ("input1.txt", "first input"),
        ("output1.txt", "first output"),
        ("input2.txt", "second input"),
        ("output2.txt", "second output"),
    ])

    await service_test_case.import_tests_zip(task.id, archive, db)

    test_cases = await get_test_cases_for_task(db, task.id)
    assert len(test_cases) == 2
    assert [test_case.task_id for test_case in test_cases] == [task.id, task.id]
    assert [test_case.input for test_case in test_cases] == ["first input", "second input"]
    assert [test_case.expected_output for test_case in test_cases] == [
        "first output",
        "second output",
    ]
    assert [test_case.order for test_case in test_cases] == [1, 2]
    assert all(test_case.is_hidden is True for test_case in test_cases)


@pytest.mark.asyncio
async def test_import_tests_zip_replaces_existing_test_cases(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    old_cases = [
        await create_test_case(db, task.id, input_value=f"old {order}", order=order)
        for order in range(1, 4)
    ]
    await service_test_case.import_tests_zip(
        task.id,
        upload_file([("input1.txt", "new input"), ("output1.txt", "new output")]),
        db,
    )

    test_cases = await get_test_cases_for_task(db, task.id)
    assert len(test_cases) == 1
    assert test_cases[0].input == "new input"
    assert test_cases[0].expected_output == "new output"
    assert all(test_case.input not in {"old 1", "old 2", "old 3"} for test_case in test_cases)


@pytest.mark.asyncio
async def test_import_tests_zip_task_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_test_case.import_tests_zip(
            999_999,
            upload_file([("input1.txt", "input"), ("output1.txt", "output")]),
            db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_import_tests_zip_rejects_invalid_extension(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    task_id = task.id

    with pytest.raises(HTTPException) as exc:
        await service_test_case.import_tests_zip(
            task_id,
            upload_file([], filename="tests.txt"),
            db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_import_tests_zip_rejects_invalid_zip_archive(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    archive = UploadFile(filename="tests.zip", file=BytesIO(b"not a zip archive"))

    with pytest.raises(HTTPException) as exc:
        await service_test_case.import_tests_zip(task.id, archive, db)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_import_tests_zip_rejects_empty_zip(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    with pytest.raises(HTTPException) as exc:
        await service_test_case.import_tests_zip(task.id, upload_file([]), db)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "files",
    [
        [("input1.txt", "input")],
        [("output1.txt", "output")],
    ],
    ids=["missing-output", "missing-input"],
)
async def test_import_tests_zip_rejects_incomplete_pair(section_factory, db, files):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    with pytest.raises(HTTPException) as exc:
        await service_test_case.import_tests_zip(task.id, upload_file(files), db)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
@pytest.mark.parametrize("duplicate_name", ["input1.txt", "output1.txt"])
async def test_import_tests_zip_rejects_duplicate_file(
    section_factory,
    db,
    duplicate_name,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    files = [
        ("input1.txt", "input"),
        ("output1.txt", "output"),
        (duplicate_name, "duplicate"),
    ]

    with pytest.warns(UserWarning, match="Duplicate name"):
        archive = upload_file(files)
    with pytest.raises(HTTPException) as exc:
        await service_test_case.import_tests_zip(task.id, archive, db)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_import_tests_zip_rejects_invalid_filename(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    with pytest.raises(HTTPException) as exc:
        await service_test_case.import_tests_zip(
            task.id,
            upload_file([("hello.txt", "hello")]),
            db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_import_tests_zip_rejects_non_utf8_content(section_factory, db):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)

    with pytest.raises(HTTPException) as exc:
        await service_test_case.import_tests_zip(
            task.id,
            upload_file([("input1.txt", b"\xff"), ("output1.txt", "output")]),
            db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_import_tests_zip_rolls_back_existing_cases_on_invalid_utf8(
    section_factory,
    db,
):
    step = await create_step(db, section_factory)
    task = await create_task(db, step.id)
    task_id = task.id
    originals = [
        await create_test_case(
            db,
            task_id,
            input_value=f"original input {order}",
            expected_output=f"original output {order}",
            order=order,
        )
        for order in range(1, 3)
    ]
    original_ids = [test_case.id for test_case in originals]

    with pytest.raises(HTTPException) as exc:
        await service_test_case.import_tests_zip(
            task_id,
            upload_file([("input1.txt", b"\xff"), ("output1.txt", "new output")]),
            db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    test_cases = await get_test_cases_for_task(db, task_id)
    assert [test_case.id for test_case in test_cases] == original_ids
    assert [test_case.input for test_case in test_cases] == [
        "original input 1",
        "original input 2",
    ]
