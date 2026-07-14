from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.exceptions import SubmissionNotFoundError, TestsNotFound
from app.models import TestCase, Submission, Task
from app.enums import SubmissionStatus

async def get_tests(task_id: int, db: AsyncSession):
    tests = (await db.execute(
        select(TestCase)
            .where(TestCase.task_id == task_id)
            .order_by(TestCase.order)
        )).scalars().all()
    if not tests:
        raise TestsNotFound(task_id=task_id)
    return tests


async def get_submission(submission_id: int, db: AsyncSession) -> Submission:
    submission = await db.get(Submission, submission_id)
    return submission

async def update_status(status: SubmissionStatus, submission: Submission, db: AsyncSession):
    submission.status = status
    await db.commit()


async def update_submission(
    submission: Submission,
    status: SubmissionStatus,
    passed_tests: int,
    total_tests: int,
    failed_test_id: int | None,
    actual_output: str | None,
    db: AsyncSession
):
    submission.status = status
    submission.passed_tests = passed_tests
    submission.total_tests = total_tests
    submission.failed_test_id = failed_test_id
    submission.actual_output = actual_output
    await db.commit()
    

async def update_status_by_submission_id(status: SubmissionStatus, submission_id: int, db: AsyncSession):
    submission = await db.get(Submission, submission_id)
    if not submission:
        raise SubmissionNotFoundError()
    await update_status(status=status, submission=submission, db=db)


async def get_task(task_id: int, db: AsyncSession) -> Task:
    task = await db.get(Task, task_id)
    return task
