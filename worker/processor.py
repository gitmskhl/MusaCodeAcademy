import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
import app.core.logging

from app.models import Submission, TestCase, Task
from app.core.database import AsyncSessionLocal
from app.core.exceptions import (
    SubmissionNotFoundError,
    TaskNotFoundError,
    TestsNotFound
)
from app.queue.submission import enqueu
from app.enums import SubmissionStatus
from worker.runner import run_code
from worker.checker import compare
from worker.services import get_tests, get_submission, update_status, get_task, update_status_by_submission_id, update_submission
from worker.models import TestsResult

logger = logging.getLogger(__name__)


async def _start_submission_processing(submission_id: int, db: AsyncSession):
    submission = await get_submission(submission_id=submission_id, db=db)
    if submission is None:
        raise SubmissionNotFoundError()
    task = await get_task(task_id=submission.task_id, db=db)
    if task is None:
        raise TaskNotFoundError(task_id=submission.task_id)
    await update_status(
        status=SubmissionStatus.RUNNING,
        submission=submission,
        db=db
    )
    return task, submission


async def _check_tests(submission_id: int, submission: Submission, task: Task, tests: list[TestCase]) -> TestsResult:
    status_result = SubmissionStatus.ACCEPTED
    logger.info(
        "Started checking submission %s",
        submission_id
    )
    passed_tests = 0
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
        passed_tests += 1
    logger.info(
        "Submission %s finished with status %s",
        submission_id,
        status_result.name
    )
    return TestsResult(
        status=status_result,
        passed_tests=passed_tests,
        total_tests=len(tests),
        failed_test_id=None if status_result == SubmissionStatus.ACCEPTED else test.id,
        actual_output= result.stdout if (status_result != SubmissionStatus.ACCEPTED) and not test.is_hidden else (result.stderr[:10000] if status_result == SubmissionStatus.RUNTIME_ERROR else None)
    )


async def process_submission(submission_id: int):
    async with AsyncSessionLocal() as db:
        try:
            task, submission = await _start_submission_processing(submission_id=submission_id, db=db)
            tests = await get_tests(task_id=submission.task_id, db=db)
            result = await _check_tests(
                submission_id=submission_id,
                submission=submission,
                task=task,
                tests=tests
            )
            await update_submission(
                submission=submission,
                status=result.status,
                passed_tests=result.passed_tests,
                total_tests=result.total_tests,
                failed_test_id=result.failed_test_id,
                actual_output=result.actual_output,
                db=db
            )
        except SubmissionNotFoundError:
            logger.warning("Submission %s not found", submission_id)
            return
        except TaskNotFoundError as e:
            logger.warning(
                "Task %s not found for submission %s",
                e.task_id,
                submission_id
            )
            await update_status_by_submission_id(
                status=SubmissionStatus.FAILED,
                submission_id=submission_id,
                db=db
            )
            return
        except TestsNotFound as e:
            logger.warning(
                "Task %s has no tests",
                e.task_id
            )
            await update_status_by_submission_id(
                status=SubmissionStatus.FAILED,
                submission_id=submission_id,
                db=db
            )
        except asyncio.CancelledError:
            logger.info(
                "Submission %s was cancelled; returning to queue",
                submission_id
            )

            try:
                await enqueu(submission_id=submission_id)
                async with AsyncSessionLocal() as cancel_db:
                    await update_status_by_submission_id(status=SubmissionStatus.PENDING, submission_id=submission_id, db=cancel_db)
            except Exception:
                logger.exception(
                    "Failed to restore submission %s",
                    submission_id
                )
            raise
        except Exception:
            logger.exception(
                "System error while processing submission %s",
                submission_id
            )
            try:
                async with AsyncSessionLocal() as error_db:
                    await update_status_by_submission_id(
                        status=SubmissionStatus.SYSTEM_ERROR,
                        submission_id=submission_id,
                        db=error_db
                    )
            except Exception:
                logger.exception(
                    "Failed to set SYSTEM_ERROR for submission %s",
                    submission_id
                )
                raise