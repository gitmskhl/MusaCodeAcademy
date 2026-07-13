import asyncio
import tempfile
from pathlib import Path
from asyncio.subprocess import PIPE
from worker.models import RunResult

async def run_code(source_code: str, test_input: str, timeout: float) -> RunResult:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        source_file = temp_path / "main.py"
        source_file.write_text(
            source_code,
            encoding="utf-8"
        )
        process = await asyncio.create_subprocess_exec(
            "python3",
            str(source_file),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(
                    input=test_input.encode("utf-8")
                ),
                timeout=timeout
            )
            return RunResult(
                stdout=stdout.decode("utf-8"),
                stderr=stderr.decode("utf-8"),
                exit_code=process.returncode
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return RunResult(
                stdout="",
                stderr="",
                exit_code=-1,
                timed_out=True
            )
        except asyncio.CancelledError:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise
    