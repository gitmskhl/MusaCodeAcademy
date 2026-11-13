"""Запись диалога программы в порядке, в котором ученик видит его в терминале."""

from functools import lru_cache
import json
import subprocess
import sys


TRACE_PROGRAM = r'''
import builtins
import contextlib
import io
import json
import sys

request = json.load(sys.stdin)
source = io.StringIO(request['input'])
events = []

class Terminal(io.TextIOBase):
    def __init__(self):
        self.pending = ''
        self.output = ''

    def write(self, value):
        self.output += value
        self.pending += value
        while '\n' in self.pending:
            line, self.pending = self.pending.split('\n', 1)
            events.append(dict(type='output', text=line))
        return len(value)

    def finish_line(self):
        if self.pending:
            events.append(dict(type='output', text=self.pending))
            self.pending = ''

terminal = Terminal()

def read(prompt=''):
    if prompt:
        terminal.write(str(prompt))
    terminal.finish_line()
    value = source.readline()
    if not value:
        raise EOFError('Пример требует больше входных строк')
    value = value.rstrip('\n').rstrip('\r')
    events.append(dict(type='input', text=value))
    return value

builtins.input = read
with contextlib.redirect_stdout(terminal):
    exec(compile(request['reference'], '<example>', 'exec'), {})
terminal.finish_line()
if source.read():
    raise ValueError('В примере остались неиспользованные входные строки')
print(json.dumps(dict(lines=events, output=terminal.output), ensure_ascii=False))
'''


@lru_cache(maxsize=512)
def trace(reference, input_data):
    process = subprocess.run(
        [sys.executable, '-I', '-c', TRACE_PROGRAM],
        input=json.dumps(dict(reference=reference, input=input_data)),
        text=True, capture_output=True, timeout=3,
    )
    if process.returncode:
        raise ValueError(f'Не удалось записать пример: {process.stderr}')
    return json.loads(process.stdout)


def checked_example(reference, case):
    recorded = trace(reference, case['input'])
    actual = recorded['output'].replace('\r\n', '\n').strip()
    expected = case['expected_output'].replace('\r\n', '\n').strip()
    if actual != expected:
        raise ValueError(f'Пример не совпадает с ожидаемым выводом: {actual!r} != {expected!r}')
    return recorded['lines']


def public_examples(item):
    if item['title'] == 'Номера шкафчиков':
        return [item['tests'][0], dict(
            input='5\n', expected_output='Сколько шкафчиков?\n1\n2\n3\n4\n5\n')]
    return item['tests'][:2]
