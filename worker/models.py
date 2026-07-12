from dataclasses import dataclass


@dataclass(slots=True)
class RunResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False