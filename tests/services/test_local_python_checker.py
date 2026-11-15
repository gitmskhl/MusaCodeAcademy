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


def function_result(source, expected=12, **options):
    case = {'function': 'max2', 'args': [5, 12], 'mode': 'return',
            'expected': expected, **options}
    encoded = harness.FUNCTION_TEST_PREFIX + json.dumps(case)
    return json.loads(harness.check_python_test(source, encoded, str(expected)))


def test_function_is_called_and_its_return_value_is_checked():
    assert function_result('def max2(a, b):\n    return max(a, b)')['status'] == 'ACCEPTED'
    assert function_result('def max2(a, b):\n    print(max(a, b))')['status'] == 'WRONG ANSWER'
    assert function_result('print(12)')['status'] == 'WRONG ANSWER'
    assert function_result('def max2(a, b):\n    return "12"')['status'] == 'WRONG ANSWER'


def test_function_arguments_are_protected_and_results_have_correct_types():
    case = {'function': 'reverse', 'args': [[1, 2]], 'expected': [2, 1],
            'mode': 'return', 'unchanged_args': True}
    encoded = harness.FUNCTION_TEST_PREFIX + json.dumps(case)
    correct = 'def reverse(items):\n    return items[::-1]'
    mutates = 'def reverse(items):\n    items.reverse()\n    return items'
    assert json.loads(harness.check_python_test(correct, encoded, '[2, 1]'))['status'] == 'ACCEPTED'
    assert json.loads(harness.check_python_test(mutates, encoded, '[2, 1]'))['status'] == 'WRONG ANSWER'
    assert function_result('def max2(a,b):\n    return 1', expected=True)['status'] == 'WRONG ANSWER'


def test_password_search_uses_the_supplied_check_function():
    import hashlib
    case = {'function': 'find_password', 'args': [], 'mode': 'password',
            'hash': hashlib.sha256(b'b').hexdigest()}
    encoded = harness.FUNCTION_TEST_PREFIX + json.dumps(case)
    source = '''def find_password():
    for c in "abc":
        if check_password(c):
            return c
'''
    assert json.loads(harness.check_python_test(source, encoded, 'Пароль найден.'))['status'] == 'ACCEPTED'
    wrong = 'def find_password():\n    return "a"'
    assert json.loads(harness.check_python_test(wrong, encoded, 'Пароль найден.'))['status'] == 'WRONG ANSWER'
