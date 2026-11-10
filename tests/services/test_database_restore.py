from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.cli.database_restore import rebuild_submission_queue
from app.core.config import settings
from app.enums import SubmissionStatus
from app.models import Lesson, Section, Step, Submission, Task, User
from app.queue.submission import QUEUE_NAME
from tests.conftest import TEST_DATABASE_URL


@pytest.mark.asyncio
async def test_queue_rebuilt_from_restored_database(db, real_course, monkeypatch):
    user = User(email="restore@example.com", password_hash="unused", first_name="Test", last_name="User")
    section = Section(course_id=real_course.id, title="Section", order=0)
    db.add_all([user, section])
    await db.flush()
    lesson = Lesson(section_id=section.id, title="Lesson", order=0)
    db.add(lesson)
    await db.flush()
    step = Step(lesson_id=lesson.id, title="Step", order=0, content={})
    db.add(step)
    await db.flush()
    task = Task(step_id=step.id)
    db.add(task)
    await db.flush()
    submissions = [Submission(task_id=task.id, user_id=user.id, source_code="print(1)", status=status,
                              passed_tests=1, actual_output="stale") for status in (
        SubmissionStatus.PENDING, SubmissionStatus.RUNNING, SubmissionStatus.ACCEPTED,
    )]
    db.add_all(submissions)
    await db.commit()
    ids = [item.id for item in submissions]
    monkeypatch.setattr(settings, "sqlalchemy_database_url", TEST_DATABASE_URL)
    pipeline = MagicMock()
    pipeline.execute = AsyncMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=pipeline)
    context.__aexit__ = AsyncMock(return_value=False)
    redis = MagicMock()
    redis.pipeline.return_value = context
    redis.aclose = AsyncMock()
    monkeypatch.setattr("app.core.redis.redis", redis)

    await rebuild_submission_queue()

    pipeline.delete.assert_called_once_with(QUEUE_NAME)
    pipeline.lpush.assert_called_once_with(QUEUE_NAME, *ids[:2])
    pipeline.execute.assert_awaited_once()
    db.expire_all()
    restored = (await db.scalars(select(Submission).order_by(Submission.id))).all()
    assert [item.status for item in restored] == [SubmissionStatus.PENDING, SubmissionStatus.PENDING, SubmissionStatus.ACCEPTED]
    assert restored[1].passed_tests == 0 and restored[1].actual_output is None
    assert restored[2].passed_tests == 1 and restored[2].actual_output == "stale"
