from app.core.database import async_sessionmaker
from app.models import Submission

async def process_submission(submission_id: int):
    async with async_sessionmaker() as db:
        submission = await db.get(Submission, submission_id)
        if not submission:
            return
        print(submission.source_code)