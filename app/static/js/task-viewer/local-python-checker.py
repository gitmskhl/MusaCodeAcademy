"""Test harness shared by the browser worker and harness regression tests."""
import io
import json
import sys
import traceback


class _LimitedBuffer(io.BytesIO):
    def write(self, data):
        if self.tell() + len(data) > 100_000:
            raise RuntimeError("Превышен допустимый объём вывода программы (100 КБ)")
        return super().write(data)


def check_python_test(source_code, test_input, expected_output):
    stdin = io.TextIOWrapper(io.BytesIO(test_input.encode("utf-8")), encoding="utf-8")
    stdout_buffer, stderr_buffer = _LimitedBuffer(), _LimitedBuffer()
    stdout = io.TextIOWrapper(stdout_buffer, encoding="utf-8", write_through=True)
    stderr = io.TextIOWrapper(stderr_buffer, encoding="utf-8", write_through=True)
    original_streams = sys.stdin, sys.stdout, sys.stderr
    original_argv = sys.argv
    status = "ACCEPTED"
    error = ""
    try:
        sys.stdin, sys.stdout, sys.stderr = stdin, stdout, stderr
        sys.argv = ["solution.py"]
        namespace = {"__name__": "__main__", "__file__": "solution.py"}
        try:
            exec(compile(source_code, "solution.py", "exec"), namespace)
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise
    except MemoryError:
        status = "MEMORY_LIMIT_EXCEEDED"
    except BaseException:
        status = "RUNTIME_ERROR"
        error = traceback.format_exc()[-10000:]
    finally:
        sys.stdin, sys.stdout, sys.stderr = original_streams
        sys.argv = original_argv

    output = stdout_buffer.getvalue().decode("utf-8", errors="replace")
    stderr_output = stderr_buffer.getvalue().decode("utf-8", errors="replace")
    # Match worker/checker.py, including Python's Unicode whitespace rules.
    normalize = lambda value: value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if status == "ACCEPTED" and normalize(output) != normalize(expected_output):
        status = "WRONG ANSWER"
    return json.dumps({
        "status": status,
        "actual_output": (error or stderr_output or output)[:10000],
    })
