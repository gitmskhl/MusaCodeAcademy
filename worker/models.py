from dataclasses import dataclass
from app.enums import SubmissionStatus

@dataclass(slots=True)
class RunResult:
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int = 0

    timed_out: bool = False
    oom_killed: bool = False


@dataclass(slots=True)
class TestsResult:
    status: SubmissionStatus
    passed_tests: int
    total_tests: int
    failed_test_id: int | None
    actual_output: str | None
