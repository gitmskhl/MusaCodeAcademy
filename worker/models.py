from dataclasses import dataclass


@dataclass(slots=True)
class RunResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
    passed_tests: int = 0
    failed_test_id: int | None = None
    actual_output: str | None = None