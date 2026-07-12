from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import TestCase, Submission, Task
from app.enums import SubmissionStatus

async def get_tests(task_id: int, db: AsyncSession):
    tests = (await db.execute(
        select(TestCase)
            .where(TestCase.task_id == task_id)
            .order_by(TestCase.order)
        )).scalars().all()
    if not tests:
        raise RuntimeError("Task has no tests")
    return tests


async def get_submission(submission_id: int, db: AsyncSession) -> Submission:
    submission = await db.get(Submission, submission_id)
    return submission


async def update_status(status: SubmissionStatus, submission: Submission, db: AsyncSession):
    submission.status = status
    await db.commit()


async def get_task(task_id: int, db: AsyncSession) -> Task:
    task = await db.get(Task, task_id)
    return task