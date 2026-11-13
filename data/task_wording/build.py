"""Проверка, экспорт и применение редакторских изменений к существующим задачам."""

import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .content import CONDITIONS, FUNCTION_NOTE, FUNCTION_STEPS

ROOT = Path(__file__).resolve().parent


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def payload():
    originals = json.loads((ROOT / 'originals.json').read_text(encoding='utf-8'))
    if {item['step_id'] for item in originals} != set(CONDITIONS):
        raise ValueError('Список исходных задач не совпадает со списком правок')
    result = []
    for item in originals:
        content = deepcopy(item['content'])
        first = content['blocks'][0]
        if first['type'] != 'text':
            raise ValueError(f"Степ {item['step_id']}: ожидался текст условия")
        wording = CONDITIONS[item['step_id']]
        if item['step_id'] in FUNCTION_STEPS:
            wording += '\n\n' + FUNCTION_NOTE
        # Подписи к примерам могут находиться в первом или в отдельном блоке.
        for label in ('Пример выполнения:', 'Примеры работы готовой программы:'):
            if first['data']['text'].endswith(label):
                wording += '\n\n' + label
        first['data']['text'] = wording
        result.append({**item, 'new_content': content})
    return result


def validate(data):
    from pydantic import TypeAdapter
    from app.schemas.steps.step_layout import StepContent

    adapter = TypeAdapter(StepContent)
    for item in data:
        adapter.validate_python(item['new_content'])
        old = deepcopy(item['content'])
        old['blocks'][0]['data']['text'] = item['new_content']['blocks'][0]['data']['text']
        if old != item['new_content']:
            raise ValueError('Разрешено менять только текст первого блока')
        if item['new_content'] == item['content']:
            raise ValueError('Пустая правка')
    print(f'Проверено {len(data)} условий. Примеры и остальные блоки сохранены.')


def export(data):
    lines = ['# Понятные условия задач', '',
             'Выбранные задачи курса «Python. Основы», начиная с циклов. '
             'В терминальных примерах строки с `>` — ввод пользователя, остальные — вывод программы.', '']
    previous = None
    for item in data:
        group = (item['section'], item['lesson'])
        if group != previous:
            lines.extend([f'## {group[0]} · {group[1]}', ''])
            previous = group
        lines.extend([f"### {item['title']}", '', f"Степ {item['step_id']}.", ''])
        for block in item['new_content']['blocks']:
            if block['type'] == 'text':
                lines.extend([block['data']['text'], ''])
            elif block['type'] == 'console':
                lines.extend(['```text', '\n'.join(
                    ('> ' if line['type'] == 'input' else '') + line['text']
                    for line in block['data']['lines']), '```', ''])
    (ROOT / 'materials.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Создан materials.md с условиями и прежними открытыми примерами.')


async def apply(data, course_id, restore=False):
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, engine
    from app.models import Course, Section, Lesson, Step, Task, TestCase

    try:
        async with AsyncSessionLocal() as session, session.begin():
            course = await session.get(Course, course_id)
            if course is None or course.title != 'Python. Основы':
                raise ValueError('Ожидался курс «Python. Основы»')
            changes = []
            for item in data:
                step = await session.scalar(select(Step).join(Lesson).join(Section).where(
                    Step.id == item['step_id'], Section.course_id == course_id).with_for_update(of=Step))
                if step is None or (step.title, step.lesson_id) != (item['title'], item['lesson_id']):
                    raise ValueError(f"Не совпадает задача степа {item['step_id']}")
                task = await session.scalar(select(Task).where(Task.step_id == step.id).with_for_update())
                if task is None:
                    raise ValueError(f'Нет задачи у степа {step.id}')
                tests = (await session.scalars(select(TestCase).where(
                    TestCase.task_id == task.id).order_by(TestCase.order).with_for_update())).all()
                contract = dict(task_id=task.id, starter_code=task.starter_code,
                                checking_mode=task.checking_mode.value,
                                tests=[dict(id=t.id, input=t.input, expected_output=t.expected_output,
                                            is_hidden=t.is_hidden, order=t.order) for t in tests])
                if fingerprint(contract) != item['contract_sha256']:
                    raise ValueError(f'У степа {step.id} изменились заготовка или проверка')
                source, target = item['content'], item['new_content']
                if restore:
                    source, target = target, source
                if step.content == target:
                    continue
                if step.content != source:
                    raise ValueError(f'Условие степа {step.id} уже отредактировано; запись отменена')
                changes.append((step, deepcopy(target)))
            if changes:
                backup_root = ROOT.parents[1] / 'backups' / 'task_wording'
                backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
                backup = backup_root / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
                backup.write_text(json.dumps(
                    [dict(step_id=step.id, title=step.title, content=step.content) for step, _ in changes],
                    ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                backup.chmod(0o600)
                for step, content in changes:
                    step.content = content
                await session.flush()
                print(f'Копия прежних условий: {backup}')
            count = len(changes)
        print(f'Транзакция завершена. Изменено условий: {count}.')
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--export', action='store_true')
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--apply', action='store_true')
    actions.add_argument('--restore', action='store_true')
    parser.add_argument('--course-id', type=int)
    args = parser.parse_args()
    if (args.apply or args.restore) and args.course_id is None:
        parser.error('--apply и --restore требуют --course-id')
    data = payload()
    validate(data)
    if args.export:
        export(data)
    if args.apply or args.restore:
        asyncio.run(apply(data, args.course_id, restore=args.restore))


if __name__ == '__main__':
    main()
