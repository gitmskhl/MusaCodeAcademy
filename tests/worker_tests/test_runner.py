import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from worker import runner
from worker.models import RunResult


class FakeContainer:
    def __init__(
        self,
        stdout: bytes = b"",
        stderr: bytes = b"",
        stdout_chunks: list[bytes] | None = None,
        stderr_chunks: list[bytes] | None = None,
        exit_code: int = 0,
        oom_killed: bool = False,
        start_error: Exception | None = None,
        wait_error: Exception | None = None,
        reload_error: Exception | None = None,
        logs_error: Exception | None = None,
        remove_error: Exception | None = None,
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.stdout_chunks = stdout_chunks
        self.stderr_chunks = stderr_chunks
        self.start_error = start_error
        self.wait_error = wait_error
        self.reload_error = reload_error
        self.logs_error = logs_error
        self.remove_error = remove_error
        self.attrs = {
            "State": {
                "ExitCode": exit_code,
                "OOMKilled": oom_killed,
            }
        }
        self.started = False
        self.killed = False
        self.waited = False
        self.reloaded = False
        self.removed = False
        self.remove_force = None

    def start(self):
        if self.start_error:
            raise self.start_error
        self.started = True

    def wait(self):
        if self.wait_error:
            raise self.wait_error
        self.waited = True
        return {"StatusCode": self.attrs["State"]["ExitCode"]}

    def kill(self):
        self.killed = True
        self.attrs["State"]["ExitCode"] = -1

    def reload(self):
        if self.reload_error:
            raise self.reload_error
        self.reloaded = True

    def logs(self, stream=False, stdout=False, stderr=False, follow=False):
        if self.logs_error:
            raise self.logs_error
        if stdout:
            data = self.stdout
            chunks = self.stdout_chunks
        elif stderr:
            data = self.stderr
            chunks = self.stderr_chunks
        else:
            data = b""
            chunks = None

        if stream:
            return iter(chunks if chunks is not None else [data])
        return data

    def remove(self, force=False):
        self.removed = True
        self.remove_force = force
        if self.remove_error:
            raise self.remove_error


def patch_container_create(monkeypatch, container, calls=None):
    def create(**kwargs):
        if calls is not None:
            call = dict(kwargs)
            volume_path = Path(next(iter(kwargs["volumes"])))
            call["source_text"] = (volume_path / "main.py").read_text(
                encoding="utf-8"
            )
            call["input_text"] = (volume_path / "input.txt").read_text(
                encoding="utf-8"
            )
            calls.append(call)
        return container

    monkeypatch.setattr(
        runner,
        "client",
        SimpleNamespace(containers=SimpleNamespace(create=create)),
    )


def patch_container_create_error(monkeypatch, error):
    def create(**kwargs):
        raise error

    monkeypatch.setattr(
        runner,
        "client",
        SimpleNamespace(containers=SimpleNamespace(create=create)),
    )


@pytest.mark.asyncio
async def test_run_simple_program_returns_stdout_and_sends_stdin(monkeypatch):
    container = FakeContainer(stdout=b"MCA\n")
    calls = []
    patch_container_create(monkeypatch, container, calls)

    result = await runner.run_code(
        source_code="print(input())",
        test_input="MCA",
        timeout=2,
    )

    assert result.stdout == "MCA\n"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.oom_killed is False
    assert calls[0]["input_text"] == "MCA"
    assert container.started is True
    assert container.reloaded is True
    assert container.removed is True
    assert container.remove_force is True


@pytest.mark.asyncio
async def test_runtime_error_returns_stderr_and_nonzero_exit_code(monkeypatch):
    container = FakeContainer(
        stderr=b"Traceback (most recent call last):\nZeroDivisionError\n",
        exit_code=1,
    )
    patch_container_create(monkeypatch, container)

    result = await runner.run_code(
        source_code="print(1 / 0)",
        test_input="",
        timeout=2,
    )

    assert result.stdout == ""
    assert "ZeroDivisionError" in result.stderr
    assert result.exit_code == 1
    assert result.timed_out is False
    assert result.oom_killed is False


@pytest.mark.asyncio
async def test_oom_killed_returns_memory_flag_and_container_state(monkeypatch):
    container = FakeContainer(
        stderr=b"Killed\n",
        exit_code=137,
        oom_killed=True,
    )
    patch_container_create(monkeypatch, container)

    result = await runner.run_code(
        source_code="lst = []\nwhile True:\n    lst.append(1)",
        test_input="",
        timeout=2,
    )

    assert result.stdout == ""
    assert result.stderr == "Killed\n"
    assert result.exit_code == 137
    assert result.timed_out is False
    assert result.oom_killed is True
    assert container.reloaded is True
    assert container.removed is True


@pytest.mark.asyncio
async def test_timeout_kills_process_and_returns_timed_out(monkeypatch):
    container = FakeContainer()
    patch_container_create(monkeypatch, container)

    async def raise_timeout(coro, timeout):
        coro.close()
        raise asyncio.TimeoutError

    monkeypatch.setattr(runner.asyncio, "wait_for", raise_timeout)

    result = await runner.run_code(
        source_code="while True: pass",
        test_input="",
        timeout=1,
    )

    assert result.stdout == ""
    assert result.stderr == ""
    assert result.exit_code == -1
    assert result.timed_out is True
    assert container.killed is True
    assert container.waited is True
    assert container.removed is True


@pytest.mark.asyncio
async def test_cancelled_run_kills_process_and_reraises(monkeypatch):
    container = FakeContainer()
    patch_container_create(monkeypatch, container)

    async def raise_cancelled(coro, timeout):
        coro.close()
        raise asyncio.CancelledError

    monkeypatch.setattr(runner.asyncio, "wait_for", raise_cancelled)

    with pytest.raises(asyncio.CancelledError):
        await runner.run_code(
            source_code="while True: pass",
            test_input="",
            timeout=1,
        )

    assert container.killed is True
    assert container.waited is True
    assert container.removed is True


@pytest.mark.asyncio
async def test_container_create_error_returns_run_result(monkeypatch):
    patch_container_create_error(monkeypatch, RuntimeError("docker unavailable"))

    result = await runner.run_code(
        source_code="print('ok')",
        test_input="",
        timeout=2,
    )

    assert result.stdout == ""
    assert result.stderr == "RuntimeError: docker unavailable"
    assert result.exit_code == -1
    assert result.timed_out is False
    assert result.oom_killed is False


@pytest.mark.asyncio
async def test_container_start_error_returns_run_result_and_removes_container(monkeypatch):
    container = FakeContainer(start_error=RuntimeError("start failed"))
    patch_container_create(monkeypatch, container)

    result = await runner.run_code(
        source_code="print('ok')",
        test_input="",
        timeout=2,
    )

    assert result.stdout == ""
    assert result.stderr == "RuntimeError: start failed"
    assert result.exit_code == -1
    assert result.timed_out is False
    assert result.oom_killed is False
    assert container.removed is True
    assert container.remove_force is True


@pytest.mark.asyncio
async def test_container_wait_error_returns_run_result_and_removes_container(monkeypatch):
    container = FakeContainer(wait_error=RuntimeError("wait failed"))
    patch_container_create(monkeypatch, container)

    result = await runner.run_code(
        source_code="print('ok')",
        test_input="",
        timeout=2,
    )

    assert result.stdout == ""
    assert result.stderr == "RuntimeError: wait failed"
    assert result.exit_code == -1
    assert result.timed_out is False
    assert result.oom_killed is False
    assert container.started is True
    assert container.removed is True


@pytest.mark.asyncio
async def test_container_reload_error_returns_run_result_and_removes_container(monkeypatch):
    container = FakeContainer(reload_error=RuntimeError("reload failed"))
    patch_container_create(monkeypatch, container)

    result = await runner.run_code(
        source_code="print('ok')",
        test_input="",
        timeout=2,
    )

    assert result.stdout == ""
    assert result.stderr == "RuntimeError: reload failed"
    assert result.exit_code == -1
    assert result.timed_out is False
    assert result.oom_killed is False
    assert container.started is True
    assert container.waited is True
    assert container.removed is True


@pytest.mark.asyncio
async def test_container_log_error_returns_run_result_and_removes_container(monkeypatch):
    container = FakeContainer(logs_error=RuntimeError("logs failed"))
    patch_container_create(monkeypatch, container)

    result = await runner.run_code(
        source_code="print('ok')",
        test_input="",
        timeout=2,
    )

    assert result.stdout == ""
    assert result.stderr == "RuntimeError: logs failed"
    assert result.exit_code == -1
    assert result.timed_out is False
    assert result.oom_killed is False
    assert container.reloaded is True
    assert container.removed is True


@pytest.mark.asyncio
async def test_remove_error_is_ignored_after_successful_run(monkeypatch):
    container = FakeContainer(stdout=b"ok\n", remove_error=RuntimeError("remove failed"))
    patch_container_create(monkeypatch, container)

    result = await runner.run_code(
        source_code="print('ok')",
        test_input="",
        timeout=2,
    )

    assert result.stdout == "ok\n"
    assert result.stderr == ""
    assert result.exit_code == 0
    assert result.timed_out is False
    assert result.oom_killed is False
    assert container.removed is True


@pytest.mark.asyncio
async def test_stdout_is_truncated_to_max_output_size(monkeypatch):
    container = FakeContainer(
        stdout_chunks=[b"a" * (runner.MAX_OUTPUT_SIZE + 10)],
    )
    patch_container_create(monkeypatch, container)

    result = await runner.run_code(
        source_code="print('large output')",
        test_input="",
        timeout=2,
    )

    assert result.stdout == ("a" * runner.MAX_OUTPUT_SIZE) + "\n\n... output truncated\n"
    assert result.stderr == ""
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_stderr_is_truncated_to_max_output_size(monkeypatch):
    container = FakeContainer(
        stderr_chunks=[b"e" * (runner.MAX_OUTPUT_SIZE + 10)],
        exit_code=1,
    )
    patch_container_create(monkeypatch, container)

    result = await runner.run_code(
        source_code="raise Exception('large error')",
        test_input="",
        timeout=2,
    )

    assert result.stdout == ""
    assert result.stderr == ("e" * runner.MAX_OUTPUT_SIZE) + "\n\n... output truncated\n"
    assert result.exit_code == 1


@pytest.mark.asyncio
async def test_invalid_utf8_output_is_replaced(monkeypatch):
    container = FakeContainer(stdout=b"ok\xff\n")
    patch_container_create(monkeypatch, container)

    result = await runner.run_code(
        source_code="print('ok')",
        test_input="",
        timeout=2,
    )

    assert result.stdout == "ok\ufffd\n"
    assert result.stderr == ""
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_docker_command_uses_security_restrictions(monkeypatch):
    calls = []
    patch_container_create(monkeypatch, FakeContainer(), calls)

    await runner.run_code(
        source_code="print('ok')",
        test_input="",
        timeout=2,
    )

    kwargs = calls[0]

    assert kwargs["image"] == "musa-python-sandbox"
    assert kwargs["command"] == ["sh", "-c", "python3 main.py < input.txt"]
    assert kwargs["working_dir"] == "/sandbox"
    assert kwargs["network_mode"] == "none"
    assert kwargs["mem_limit"] == runner.MEMORY_LIMIT
    assert kwargs["nano_cpus"] == runner.CPU_LIMIT
    assert kwargs["pids_limit"] == runner.PIDS_LIMIT
    assert kwargs["read_only"] is True
    assert kwargs["tmpfs"] == {"/tmp": "rw,size=16m,noexec,nosuid,nodev"}
    assert kwargs["cap_drop"] == ["ALL"]
    assert next(iter(kwargs["volumes"].values())) == {
        "bind": "/sandbox",
        "mode": "ro",
    }


@pytest.mark.asyncio
async def test_source_and_input_are_not_passed_as_command_arguments(monkeypatch):
    calls = []
    malicious_source = 'print("ok"); __import__("os").system("rm -rf /")'
    malicious_input = '"; rm -rf / #'
    patch_container_create(monkeypatch, FakeContainer(stdout=b"ok\n"), calls)

    await runner.run_code(
        source_code=malicious_source,
        test_input=malicious_input,
        timeout=2,
    )

    kwargs = calls[0]
    command = " ".join(kwargs["command"])

    assert kwargs["source_text"] == malicious_source
    assert kwargs["input_text"] == malicious_input
    assert malicious_source not in command
    assert malicious_input not in command
