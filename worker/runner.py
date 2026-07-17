import asyncio
import tempfile
import docker
from docker.models.containers import Container
import time
from typing import Literal
from pathlib import Path
from worker.models import RunResult

client = docker.from_env()

MEMORY_LIMIT = "64m"
CPU_LIMIT = 1_000_000_000
PIDS_LIMIT = 8
MAX_OUTPUT_SIZE = 64 * 1024 # 64KB


def read_logs(
    container: Container,
    stream: Literal["stdout", "stderr"]
) -> str:
    chunks = []
    total_size = 0

    log_stream = container.logs(
        stream=True,
        stdout=(stream == "stdout"),
        stderr=(stream == "stderr"),
        follow=False
    )

    for chunk in log_stream:
        remaining = MAX_OUTPUT_SIZE - total_size

        if remaining <= 0:
            chunks.append(b"\n\n... output truncated\n")
            break
        if len(chunk) > remaining:
            chunks.append(chunk[:remaining])
            total_size += remaining
            chunks.append(b"\n\n... output truncated\n")
            break
        chunks.append(chunk)
        total_size += len(chunk)

    return b"".join(chunks).decode(
        "utf-8",
        errors="replace"
    )

async def run_code(source_code: str, test_input: str, timeout: float) -> RunResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_file = temp_path / "main.py"
        source_file.write_text(
            source_code,
            encoding="utf-8"
        )
        input_file = temp_path / "input.txt"
        input_file.write_text(
            test_input,
            encoding="utf-8"
        )
        container = None
        start = time.perf_counter()
        try:
            container = client.containers.create(
                image="musa-python-sandbox",
                command=["sh", "-c", "python3 main.py < input.txt"],
                working_dir="/sandbox",
                volumes={
                    str(temp_path.resolve()): {
                        "bind": "/sandbox",
                        "mode": "ro"
                    }
                },
                network_mode="none",
                mem_limit=MEMORY_LIMIT,
                nano_cpus=CPU_LIMIT,
                read_only=True,
                tmpfs={"/tmp": "rw,size=16m,noexec,nosuid,nodev"},
                cap_drop=["ALL"],
                pids_limit=PIDS_LIMIT,
                security_opt=["no-new-privileges"]
            )

            await asyncio.to_thread(container.start)

            try:
                await asyncio.wait_for(
                    asyncio.to_thread(container.wait),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                await asyncio.to_thread(container.kill)
                await asyncio.to_thread(container.wait)

                return RunResult(
                    stdout="",
                    stderr="",
                    exit_code=-1,
                    execution_time_ms=int(
                        (time.perf_counter() - start) * 1000
                    ),
                    timed_out=True,
                    oom_killed=False
                )
            
            await asyncio.to_thread(container.reload)

            stdout = await asyncio.to_thread(
                read_logs,
                container,
                "stdout"
            )

            stderr = await asyncio.to_thread(
                read_logs,
                container,
                "stderr"
            )

            state = container.attrs["State"]
            return RunResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=state['ExitCode'],
                execution_time_ms=int(
                    (time.perf_counter() - start) * 1000
                ),
                timed_out=False,
                oom_killed=state["OOMKilled"]
            )

        except asyncio.CancelledError:
            if container is not None:
                try:
                    await asyncio.to_thread(container.kill)
                    await asyncio.to_thread(container.wait)
                except Exception:
                    pass
            raise

        except Exception as e:
            return RunResult(
                stdout="",
                stderr=f"{type(e).__name__}: {e}",
                exit_code=-1,
                execution_time_ms=int(
                    (time.perf_counter() - start) * 1000
                ),
                timed_out=False,
                oom_killed=False
            )

        finally:
            if container is not None:
                try:
                    await asyncio.to_thread(
                        container.remove,
                        force=True
                    )
                except Exception:
                    pass
