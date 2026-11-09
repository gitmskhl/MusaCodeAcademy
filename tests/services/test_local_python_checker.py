"""Exercise the same Python harness that is loaded by the Pyodide worker."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest


spec = importlib.util.spec_from_file_location(
    'local_python_checker',
    Path(__file__).resolve().parents[2] / 'app/static/js/task-viewer/local-python-checker.py',
)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


@pytest.mark.parametrize('source,stdin,expected,status', [
    ('print(int(input()) * 2)', '2\n', '4', 'ACCEPTED'),
    ('print(4)', '', '6', 'WRONG ANSWER'),
    ('print("Привет")', '', 'Привет\r\n', 'ACCEPTED'),
    ('print("\\x1c4\\x1c")', '', '4', 'ACCEPTED'),
    ('import sys\nsys.stdout.buffer.write(sys.stdin.buffer.read())', 'Привет\n', 'Привет', 'ACCEPTED'),
    ('print(4)\nraise SystemExit(0)', '', '4', 'ACCEPTED'),
    ('raise SystemExit(2)', '', '', 'RUNTIME_ERROR'),
    ('print(1 / 0)', '', '', 'RUNTIME_ERROR'),
    ('if:', '', '', 'RUNTIME_ERROR'),
    ('input()', '', '', 'RUNTIME_ERROR'),
    ('raise MemoryError()', '', '', 'MEMORY_LIMIT_EXCEEDED'),
    ('print("a" * 200000)', '', '', 'RUNTIME_ERROR'),
])
def test_local_python_checker(source, stdin, expected, status):
    streams = sys.stdin, sys.stdout, sys.stderr
    result = json.loads(harness.check_python_test(source, stdin, expected))
    assert result['status'] == status
    assert (sys.stdin, sys.stdout, sys.stderr) == streams
    assert len(result['actual_output']) <= 10000


def test_namespace_is_fresh_for_each_test():
    source = 'counter = globals().get("counter", 0) + 1\nprint(counter)'
    for _ in range(2):
        result = json.loads(harness.check_python_test(source, '', '1'))
        assert result['status'] == 'ACCEPTED'
