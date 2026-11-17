"""Test harness shared by the browser worker and harness regression tests."""
import io
import json
import sys
import traceback
from copy import deepcopy


FUNCTION_TEST_PREFIX = '# mca:function-test:v1\n'


def _check_function(namespace, case):
    """Call a student's function with JSON arguments, without evaluating test code."""
    import hashlib

    if case['mode'] == 'password':
        def check_password(candidate):
            return hashlib.sha256(candidate.encode('utf-8')).hexdigest() == case['hash']
        namespace['check_password'] = check_password
    arguments = deepcopy(case['args'])
    result = namespace[case['function']](*arguments)
    if case.get('unchanged_args') and arguments != case['args']:
        raise AssertionError('Функция изменила исходный список.')
    if case.get('unchanged_args') and any(result is arg for arg in arguments if isinstance(arg, list)):
        raise AssertionError('Нужно вернуть новый список.')
    if case['mode'] == 'password':
        if not isinstance(result, str) or not 1 <= len(result) <= 4 or any(
                c not in 'abcdefghijklmnopqrstuvwxyz0123456789' for c in result):
            raise AssertionError('Верни пароль строкой из 1–4 допустимых символов.')
        if not check_password(result):
            raise AssertionError('Возвращённая строка не подходит.')
        print('Пароль найден.')
    elif case['mode'] == 'return':
        expected = case['expected']
        if type(result) is not type(expected) or result != expected:
            raise AssertionError('Неверное возвращаемое значение: ' + repr(result))
        print(result)
    elif result is not None:
        raise AssertionError('Эта функция должна выводить результат, а не возвращать значение.')


class _LimitedBuffer(io.BytesIO):
    def write(self, data):
        if self.tell() + len(data) > 100_000:
            raise RuntimeError("Превышен допустимый объём вывода программы (100 КБ)")
        return super().write(data)


def check_python_test(source_code, test_input, expected_output):
    function_case = (json.loads(test_input[len(FUNCTION_TEST_PREFIX):])
                     if test_input.startswith(FUNCTION_TEST_PREFIX) else None)
    stdin_text = '' if function_case else test_input
    stdin = io.TextIOWrapper(io.BytesIO(stdin_text.encode("utf-8")), encoding="utf-8")
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
        if function_case:
            if stdout_buffer.getvalue():
                raise AssertionError('Отправь определения функций без примеров вызова и вывода.')
            _check_function(namespace, function_case)
    except MemoryError:
        status = "MEMORY_LIMIT_EXCEEDED"
    except AssertionError as exc:
        status = 'WRONG ANSWER' if function_case else 'RUNTIME_ERROR'
        error = str(exc) if function_case else traceback.format_exc()[-10000:]
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
        # A comparison failure must carry the stdout that was compared. Stderr
        # may contain arbitrary text and cannot explain an output mismatch.
        "actual_output": (output if status == 'WRONG ANSWER' and not error
                          else error or stderr_output or output)[:10000],
    })
