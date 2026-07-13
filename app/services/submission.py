from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from fastapi import status, HTTPException
from app.schemas.submission import SubmissionCreate
from app.models import Submission, Task, Step, Lesson, Section
from app.enums import SubmissionStatus
from app.queue.submission import enqueu

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
    new_submission = Submission(
        task_id=submissionInfo.task_id,
        user_id=user_id,
        source_code=submissionInfo.source_code,
        status=SubmissionStatus.PENDING
    )
    db.add(new_submission)
    try:
        await db.commit()
        await db.refresh(new_submission)
        await enqueu(submission_id=new_submission.id)
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

