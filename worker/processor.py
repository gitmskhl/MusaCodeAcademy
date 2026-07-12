from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import Submission, TestCase
from app.enums import SubmissionStatus


async def process_submission(submission_id: int):
    async with AsyncSessionLocal() as db:
        submission = await db.get(Submission, submission_id)
        if not submission:
            return
        submission.status = SubmissionStatus.RUNNING
        await db.commit()
        
        tests = (await db.execute(
            select(TestCase)
                .where(TestCase.task_id == submission.task_id)
                .order_by(TestCase.order)
        )).scalars().all()
        for test in tests:
            print('-' * 100)
            print(test.input)
            print(test.expected_output)

        print(submission.source_code)