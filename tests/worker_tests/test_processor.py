import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.enums import SubmissionStatus
from worker.models import RunResult, TestsResult as WorkerTestsResult
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
            id=1,
            input="hello",
            expected_output="hello",
            is_hidden=False
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
    assert result == WorkerTestsResult(
        status=SubmissionStatus.ACCEPTED,
        passed_tests=1,
        total_tests=1,
        failed_test_id=None,
        actual_output=None
    )


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
                id=11,
                input="",
                expected_output='correct',
                is_hidden=False
            )
        ]
    )

    assert result == WorkerTestsResult(
        status=SubmissionStatus.WRONG_ANSWER,
        passed_tests=0,
        total_tests=1,
        failed_test_id=11,
        actual_output="wrong"
    )


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
                id=12,
                input="",
                expected_output="",
                is_hidden=True
            )
        ]
    )
    assert result == WorkerTestsResult(
        status=SubmissionStatus.TIME_LIMIT_EXCEEDED,
        passed_tests=0,
        total_tests=1,
        failed_test_id=12,
        actual_output=None
    )


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
                id=13,
                input="",
                expected_output="",
                is_hidden=False
            )
        ]
    )
    assert result.status == SubmissionStatus.RUNTIME_ERROR
    assert result.passed_tests == 0
    assert result.total_tests == 1
    assert result.failed_test_id == 13


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
                id=14,
                input="",
                expected_output="correct",
                is_hidden=False
            ),
            SimpleNamespace(
                id=15,
                input="",
                expected_output="correct",
                is_hidden=False
            )
        ]
    )
    assert result.status == SubmissionStatus.WRONG_ANSWER
    assert result.passed_tests == 0
    assert result.total_tests == 2
    assert result.failed_test_id == 14
    assert result.actual_output == "wrong"
    assert run_code_mock.await_count == 1


@pytest.mark.asyncio
async def test_check_tests_hides_actual_output_for_hidden_test(monkeypatch):
    monkeypatch.setattr(processor, "run_code", AsyncMock(
        return_value=RunResult(stdout="secret output", stderr="", exit_code=0)
    ))

    result = await processor._check_tests(
        submission_id=1,
        submission=SimpleNamespace(source_code="print('secret output')"),
        task=SimpleNamespace(time_limit_ms=1000),
        tests=[SimpleNamespace(
            id=16,
            input="",
            expected_output="correct",
            is_hidden=True
        )]
    )

    assert result.actual_output is None


class FakeSessionContext:
    def __init__(self):
        self.session = object()
    
    async def __aenter__(self):
        return self.session
    
    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_process_submission_saves_tests_result(monkeypatch):
    session_context = FakeSessionContext()
    monkeypatch.setattr(processor, "AsyncSessionLocal", lambda: session_context)

    task = SimpleNamespace(id=20, time_limit_ms=1000)
    submission = SimpleNamespace(id=10, task_id=20, source_code="print('wrong')")
    tests = [SimpleNamespace(id=17)]
    tests_result = WorkerTestsResult(
        status=SubmissionStatus.WRONG_ANSWER,
        passed_tests=2,
        total_tests=5,
        failed_test_id=17,
        actual_output="wrong answer"
    )
    update_submission_mock = AsyncMock()

    monkeypatch.setattr(
        processor,
        "_start_submission_processing",
        AsyncMock(return_value=(task, submission))
    )
    monkeypatch.setattr(processor, "get_tests", AsyncMock(return_value=tests))
    monkeypatch.setattr(processor, "_check_tests", AsyncMock(return_value=tests_result))
    monkeypatch.setattr(processor, "update_submission", update_submission_mock)

    await processor.process_submission(submission_id=10)

    processor.get_tests.assert_awaited_once_with(task_id=20, db=session_context.session)
    processor._check_tests.assert_awaited_once_with(
        submission_id=10,
        submission=submission,
        task=task,
        tests=tests
    )
    update_submission_mock.assert_awaited_once_with(
        submission=submission,
        status=SubmissionStatus.WRONG_ANSWER,
        passed_tests=2,
        total_tests=5,
        failed_test_id=17,
        actual_output="wrong answer",
        db=session_context.session
    )
    


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
