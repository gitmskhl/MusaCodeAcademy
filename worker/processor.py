from app.models import Submission
from app.core.database import AsyncSessionLocal
from app.enums import SubmissionStatus
from worker.runner import run_code
from worker.checker import compare
from worker.services import get_tests, get_submission, update_status, get_task


async def process_submission(submission_id: int):
    async with AsyncSessionLocal() as db:
        submission = await get_submission(submission_id=submission_id, db=db)
        if submission is None:
            return
        task = await get_task(task_id=submission.task_id, db=db)
        if task is None:
            return
        await update_status(
            status=SubmissionStatus.RUNNING,
            submission=submission,
            db=db
        )

        try:
            tests = await get_tests(task_id=submission.task_id, db=db)
            status_result = SubmissionStatus.ACCEPTED

            for test in tests:
                result = await run_code(
                    source_code=submission.source_code,
                    test_input=test.input,
                    timeout=task.time_limit_ms / 1000
                )
                if result.timed_out:
                    status_result = SubmissionStatus.TIME_LIMIT_EXCEEDED
                    break
                if result.exit_code != 0:
                    status_result = SubmissionStatus.RUNTIME_ERROR
                    break
                if not compare(result.stdout, test.expected_output):
                    status_result = SubmissionStatus.WRONG_ANSWER
                    break

            await update_status(
                status=status_result,
                submission=submission,
                db=db
            )
        except Exception:
            await update_status(
                status=SubmissionStatus.SYSTEM_ERROR,
                submission=submission,
                db=db
            )
            raise
