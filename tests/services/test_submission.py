from datetime import datetime

import pytest
from unittest.mock import AsyncMock
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.enums import SubmissionStatus
from app.models import Lesson, Step, Task, Submission
from app.schemas.submission import SubmissionCreate as CreateSubmissionSchema
from app.services import submission as submission_service


async def create_step(db, section_factory, *, is_published: bool) -> Step:
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
        starter_code="print('hello')",
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
    status: SubmissionStatus = SubmissionStatus.PENDING,
    submitted_at: datetime | None = None,
) -> Submission:
    submission = Submission(
        task_id=task_id,
        user_id=user_id,
        source_code=source_code,
        status=status,
        **({"submitted_at": submitted_at} if submitted_at is not None else {}),
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


@pytest.mark.asyncio
async def test_create_submission_success_for_published_course(
    section_factory,
    db,
    monkeypatch
):
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)

    enqueu_mock = AsyncMock()
    monkeypatch.setattr(
        submission_service,
        "enqueu",
        enqueu_mock
    )

    submission = await submission_service.create_submission(
        user_id=123,
        submissionInfo=CreateSubmissionSchema(
            task_id=task.id,
            source_code="print('ok')",
        ),
        db=db,
    )

    assert submission.id is not None
    assert submission.task_id == task.id
    assert submission.user_id == 123
    assert submission.source_code == "print('ok')"
    assert submission.status == SubmissionStatus.PENDING
    assert submission.submitted_at is not None
    assert await db.get(Submission, submission.id) is not None
    enqueu_mock.assert_awaited_once_with(
        submission_id=submission.id
    )


@pytest.mark.asyncio
async def test_create_submission_task_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await submission_service.create_submission(
            user_id=123,
            submissionInfo=CreateSubmissionSchema(
                task_id=999_999,
                source_code="print('ok')",
            ),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Task not found"


@pytest.mark.asyncio
async def test_create_submission_hides_unpublished_course_task(
    section_factory,
    db,
):
    step = await create_step(db, section_factory, is_published=False)
    task = await create_task(db, step.id)

    with pytest.raises(HTTPException) as exc:
        await submission_service.create_submission(
            user_id=123,
            submissionInfo=CreateSubmissionSchema(
                task_id=task.id,
                source_code="print('ok')",
            ),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Task not found"


@pytest.mark.asyncio
async def test_create_submission_rolls_back_on_commit_error(
    section_factory,
    db,
    monkeypatch,
):
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(IntegrityError):
        await submission_service.create_submission(
            user_id=123,
            submissionInfo=CreateSubmissionSchema(
                task_id=task.id,
                source_code="print('ok')",
            ),
            db=db,
        )

    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_submission_returns_owned_submission(section_factory, db):
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    submission = await create_submission(
        db,
        task.id,
        user_id=123,
        source_code="print('mine')",
    )

    result = await submission_service.get_submission(
        submission_id=submission.id,
        user_id=123,
        db=db,
    )

    assert result.id == submission.id
    assert result.user_id == 123
    assert result.source_code == "print('mine')"


@pytest.mark.asyncio
async def test_get_submission_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await submission_service.get_submission(
            submission_id=999_999,
            user_id=123,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Submission not found"


@pytest.mark.asyncio
async def test_get_submission_rejects_other_user(section_factory, db):
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    submission = await create_submission(db, task.id, user_id=123)

    with pytest.raises(HTTPException) as exc:
        await submission_service.get_submission(
            submission_id=submission.id,
            user_id=456,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Access denied"


@pytest.mark.asyncio
async def test_get_submission_allows_admin_bypass(section_factory, db):
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    submission = await create_submission(db, task.id, user_id=123)

    result = await submission_service.get_submission(
        submission_id=submission.id,
        user_id=456,
        db=db,
        check_for_user=False,
    )

    assert result.id == submission.id


@pytest.mark.asyncio
async def test_get_submissions_filters_by_task_and_user(section_factory, db):
    first_step = await create_step(db, section_factory, is_published=True)
    first_task = await create_task(db, first_step.id)
    second_step = await create_step(db, section_factory, is_published=True)
    second_task = await create_task(db, second_step.id)
    first_submission = await create_submission(
        db,
        first_task.id,
        user_id=123,
        source_code="print('first')",
    )
    second_submission = await create_submission(
        db,
        first_task.id,
        user_id=123,
        source_code="print('second')",
    )
    await create_submission(db, first_task.id, user_id=456)
    await create_submission(db, second_task.id, user_id=123)

    result = await submission_service.get_submissions(
        task_id=first_task.id,
        user_id=123,
        db=db,
    )

    assert [submission.id for submission in result] == [
        first_submission.id,
        second_submission.id,
    ]


@pytest.mark.asyncio
async def test_get_submissions_task_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await submission_service.get_submissions(
            task_id=999_999,
            user_id=123,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Task not found"


@pytest.mark.asyncio
async def test_get_last_submission_returns_latest_for_task_and_user(
    section_factory,
    db,
):
    first_step = await create_step(db, section_factory, is_published=True)
    first_task = await create_task(db, first_step.id)
    second_step = await create_step(db, section_factory, is_published=True)
    second_task = await create_task(db, second_step.id)
    await create_submission(
        db,
        first_task.id,
        user_id=123,
        source_code="print('older')",
        submitted_at=datetime(2026, 1, 1, 10, 0),
    )
    latest = await create_submission(
        db,
        first_task.id,
        user_id=123,
        source_code="print('latest')",
        submitted_at=datetime(2026, 1, 1, 12, 0),
    )
    await create_submission(
        db,
        first_task.id,
        user_id=456,
        submitted_at=datetime(2026, 1, 1, 13, 0),
    )
    await create_submission(
        db,
        second_task.id,
        user_id=123,
        submitted_at=datetime(2026, 1, 1, 14, 0),
    )

    result = await submission_service.get_last_submission(
        task_id=first_task.id,
        user_id=123,
        db=db,
    )

    assert result is not None
    assert result.id == latest.id
    assert result.source_code == "print('latest')"


@pytest.mark.asyncio
async def test_get_last_submission_returns_none_when_user_has_no_submissions(
    section_factory,
    db,
):
    step = await create_step(db, section_factory, is_published=True)
    task = await create_task(db, step.id)
    await create_submission(db, task.id, user_id=456)

    result = await submission_service.get_last_submission(
        task_id=task.id,
        user_id=123,
        db=db,
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_last_submission_task_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await submission_service.get_last_submission(
            task_id=999_999,
            user_id=123,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Task not found"
