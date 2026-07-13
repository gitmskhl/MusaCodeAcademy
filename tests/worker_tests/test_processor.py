import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.enums import SubmissionStatus
from worker.models import RunResult
from worker import processor


@pytest.mark.asyncio
async def test_check_tests_returns_accepted(monkeypatch):
    submission = SimpleNamespace(
        source_code="print(input())"
    )
    task = SimpleNamespace(
        time_limit_ms=1000
    )
    tests = [
        SimpleNamespace(
            input="hello",
            expected_output="hello"
        )
    ]
    run_code_mock = AsyncMock(
        return_value=RunResult(
            stdout="hello\n",
            stderr="",
            exit_code=0
        )
    )
    monkeypatch.setattr(processor, "run_code", run_code_mock)
    result = await processor._check_tests(
        submission_id=1,
        submission=submission,
        task=task,
        tests=tests
    )
    assert result == SubmissionStatus.ACCEPTED


@pytest.mark.asyncio
async def test_check_tests_returns_wrong_answer(monkeypatch):
    run_code_mock = AsyncMock(
        return_value=RunResult(
            stdout="wrong",
            stderr="",
            exit_code=0
        )
    )
    monkeypatch.setattr(processor, "run_code", run_code_mock)
    result = await processor._check_tests(
        submission_id=1,
        submission=SimpleNamespace(source_code="print('wrong')"),
        task=SimpleNamespace(time_limit_ms=1000),
        tests=[
            SimpleNamespace(
                input="",
                expected_output='correct'
            )
        ]
    )

    assert result == SubmissionStatus.WRONG_ANSWER


@pytest.mark.asyncio
async def test_check_tests_returns_time_limit_exceeded(monkeypatch):
    run_code_mock = AsyncMock(
        return_value=RunResult(
            stdout="",
            stderr="",
            exit_code=-1,
            timed_out=True
        )
    )
    monkeypatch.setattr(processor, "run_code", run_code_mock)
    result = await processor._check_tests(
        submission_id=1,
        submission=SimpleNamespace(source_code="while True: pass"),
        task=SimpleNamespace(time_limit_ms=100),
        tests=[
            SimpleNamespace(
                input="",
                expected_output=""
            )
        ]
    )
    assert result == SubmissionStatus.TIME_LIMIT_EXCEEDED


@pytest.mark.asyncio
async def test_check_tests_returns_runtime_error(monkeypatch):
    run_code_mock = AsyncMock(
        return_value=RunResult(
            stdout="",
            stderr="NameError",
            exit_code=1,
        )
    )
    monkeypatch.setattr(processor, "run_code", run_code_mock)
    result = await processor._check_tests(
        submission_id=1,
        submission=SimpleNamespace(source_code="print(a)"),
        task=SimpleNamespace(time_limit_ms=1000),
        tests=[
            SimpleNamespace(
                input="",
                expected_output=""
            )
        ]
    )
    assert result == SubmissionStatus.RUNTIME_ERROR


@pytest.mark.asyncio
async def test_check_tests_stops_after_first_failure(monkeypatch):
    run_code_mock = AsyncMock(
        return_value=RunResult(
            stdout="wrong",
            stderr="",
            exit_code=0,
        )
    )
    monkeypatch.setattr(processor, "run_code", run_code_mock)
    result = await processor._check_tests(
        submission_id=1,
        submission=SimpleNamespace(source_code="print('wrong')"),
        task=SimpleNamespace(time_limit_ms=1000),
        tests=[
            SimpleNamespace(
                input="",
                expected_output="correct"
            ),
            SimpleNamespace(
                input="",
                expected_output="correct"
            )
        ]
    )
    assert result == SubmissionStatus.WRONG_ANSWER
    assert run_code_mock.await_count == 1


class FakeSessionContext:
    def __init__(self):
        self.session = object()
    
    async def __aenter__(self):
        return self.session
    
    async def __aexit__(self, exc_type, exc, tb):
        return False
    


@pytest.mark.asyncio
async def test_process_submission_restores_task_on_cancellation(monkeypatch):
    monkeypatch.setattr(processor, "AsyncSessionLocal", FakeSessionContext)
    
    task = SimpleNamespace(
        id=20,
        time_limit_ms=1000
    )
    submission = SimpleNamespace(
        id=10,
        task_id=20,
        source_code="while True: pass"
    )
    enqueue_mock = AsyncMock()
    restore_status_mock = AsyncMock()
    monkeypatch.setattr(processor, "get_task", AsyncMock(return_value=task))
    monkeypatch.setattr(processor, "get_submission", AsyncMock(return_value=submission))
    monkeypatch.setattr(processor, "update_status", AsyncMock())
    monkeypatch.setattr(processor, "update_status_by_submission_id", restore_status_mock)
    monkeypatch.setattr(processor, "get_tests", AsyncMock(
        return_value=[SimpleNamespace()]
    ))
    monkeypatch.setattr(processor, "_check_tests", AsyncMock(
        side_effect=asyncio.CancelledError
    ))
    monkeypatch.setattr(processor, "enqueu", enqueue_mock)

    with pytest.raises(asyncio.CancelledError):
        await processor.process_submission(submission_id=10)
    
    enqueue_mock.assert_awaited_once_with(submission_id=10)
    restore_status_mock.assert_awaited_once_with(
        status=SubmissionStatus.PENDING,
        submission_id=10,
        db=restore_status_mock.await_args.kwargs["db"]
    )


@pytest.mark.asyncio
async def test_process_submission_propagates_when_restore_fails(monkeypatch):
    monkeypatch.setattr(processor, "AsyncSessionLocal", FakeSessionContext)
    
    task = SimpleNamespace(
        id=20,
        time_limit_ms=1000
    )
    submission = SimpleNamespace(
        id=10,
        task_id=20,
        source_code="while True: pass"
    )
    restore_status_mock = AsyncMock()
    monkeypatch.setattr(processor, "get_task", AsyncMock(return_value=task))
    monkeypatch.setattr(processor, "get_submission", AsyncMock(return_value=submission))
    monkeypatch.setattr(processor, "update_status", AsyncMock())
    monkeypatch.setattr(processor, "update_status_by_submission_id", restore_status_mock)
    monkeypatch.setattr(processor, "get_tests", AsyncMock(
        return_value=[SimpleNamespace()]
    ))
    monkeypatch.setattr(processor, "_check_tests", AsyncMock(
        side_effect=asyncio.CancelledError
    ))
    monkeypatch.setattr(processor, "enqueu", AsyncMock(
        side_effect=ConnectionError("Redis unavailable")
    ))

    with pytest.raises(asyncio.CancelledError):
        await processor.process_submission(submission_id=10)
