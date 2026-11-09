import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert
from fastapi import status, HTTPException
from app.schemas.submission import SubmissionCreate
from app.models import Submission, Task, Step, Lesson, Section, StepProgress, TestCase
from app.enums import SubmissionStatus, TaskCheckingMode
from app.queue.submission import enqueu


logger = logging.getLogger(__name__)

async def create_submission(user_id: int, submissionInfo: SubmissionCreate, db: AsyncSession) -> Submission:
    task = (
        await db.execute(
            select(Task)
            .options(
                selectinload(Task.step)
                .selectinload(Step.lesson)
                .selectinload(Lesson.section)
                .selectinload(Section.course)
            )
            .where(Task.id == submissionInfo.task_id)
        )
    ).scalar_one_or_none()

    if not task or not task.step.lesson.section.course.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    result = submissionInfo.local_result
    is_local = task.checking_mode == TaskCheckingMode.LOCAL
    if is_local and result is None:
        raise HTTPException(status_code=409, detail="Run the tests locally before submitting")
    if not is_local and result is not None:
        raise HTTPException(status_code=409, detail="Task requires server checking")

    total_tests = None
    if is_local:
        test_ids = (await db.scalars(
            select(TestCase.id).where(TestCase.task_id == task.id)
            .order_by(TestCase.order, TestCase.id)
        )).all()
        total_tests = len(test_ids)
        if not total_tests:
            raise HTTPException(status_code=409, detail="Task has no tests")
        accepted = result.status == SubmissionStatus.ACCEPTED
        if accepted:
            valid_result = result.passed_tests == total_tests and result.failed_test_id is None
        else:
            valid_result = (
                result.passed_tests < total_tests
                and result.failed_test_id == test_ids[result.passed_tests]
            )
        if not valid_result:
            raise HTTPException(status_code=409, detail="Tests have changed or the local result is invalid; run the tests again")

    new_submission = Submission(
        task_id=submissionInfo.task_id,
        user_id=user_id,
        source_code=submissionInfo.source_code,
        status=result.status if is_local else SubmissionStatus.PENDING,
        passed_tests=result.passed_tests if is_local else 0,
        total_tests=total_tests,
        failed_test_id=result.failed_test_id if is_local else None,
        actual_output=result.actual_output if is_local else None,
    )
    db.add(new_submission)
    try:
        if is_local and result.status == SubmissionStatus.ACCEPTED:
            # Save progress atomically with the accepted submission. Concurrent
            # retries must not create duplicate progress rows.
            await db.execute(insert(StepProgress).values(
                step_id=task.step_id, user_id=user_id
            ).on_conflict_do_nothing(index_elements=["step_id", "user_id"]))
        await db.commit()
        await db.refresh(new_submission)
        if is_local:
            return new_submission
        try:
            await enqueu(submission_id=new_submission.id)
        except Exception as e:
            logger.exception("Redis error: can not enqueue %s", e)
            new_submission.status = SubmissionStatus.SYSTEM_ERROR
            await db.commit()
            await db.refresh(new_submission)
            return new_submission
        return new_submission
    except Exception:
        await db.rollback()
        raise


async def get_submission(submission_id: int, user_id: int, db: AsyncSession, check_for_user: bool = True) -> Submission:
    submission = await db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found"
        )
    if check_for_user and submission.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    return submission


async def get_submissions(task_id: int, user_id: int, db: AsyncSession) -> list[Submission]:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return (await db.execute(
        select(Submission)
            .where(and_(
                Submission.task_id == task_id,
                Submission.user_id == user_id
            ))
    )).scalars().all()


async def get_last_submission(task_id: int, user_id: int, db: AsyncSession) -> Submission | None:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return (await db.execute(
        select(Submission)
            .where(
                Submission.task_id == task_id,
                Submission.user_id == user_id
            )
            .order_by(Submission.submitted_at.desc())
            .limit(1)
    )).scalar_one_or_none()

