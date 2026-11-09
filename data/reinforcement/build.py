"""Проверка, экспорт и осторожное добавление секции в существующий курс.

Из корня проекта:
  python -m data.reinforcement.build --check
  python -m data.reinforcement.build --export
  python -m data.reinforcement.build --apply --course-id 1
"""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import sys

from .content import LESSONS

SECTION_TITLE = 'Закрепление пройденного материала'
ROOT = Path(__file__).resolve().parent


def difficulty(index, total):
    if total == 15:
        return ['Базовая', 'Средняя', 'Повышенная'][index // 5]
    return 'Базовая' if index < 3 else 'Средняя' if index < 7 else 'Повышенная'


def payload():
    result = []
    for group in LESSONS:
        tasks = []
        for index, item in enumerate(group['tasks']):
            blocks = []
            if index == 0:
                blocks.append(dict(type='text', data=dict(text=group['reminder'])))
                blocks.append(dict(type='callout', data=dict(
                    variant='info', title='Как работать с задачами',
                    content='Начни с простых задач и двигайся по порядку. Сообщения, пробелы и порядок вывода должны совпадать с примерами. Вводи только данные из условия. Каждый степ — отдельная программа. Если условие просит определенный прием, используй его: автоматическая проверка сравнивает вывод, а выбор приема проверь самостоятельно.')))
            blocks.append(dict(type='text', data=dict(text=f"### {item['title']}\n\nСложность: **{difficulty(index, len(group['tasks']))}**.\n\n{item['text']}")))
            if item['input_description']:
                blocks.append(dict(type='text', data=dict(text='**Порядок ввода:**\n\n'+item['input_description'])))
            for number, case in enumerate(item['tests'][:2], 1):
                # Отдельные блоки сохраняют видимость завершающих пробелов в консоли.
                blocks.append(dict(type='text', data=dict(text=f'**Пример {number}. Входные данные:**' if case['input'] else f'**Пример {number}. Входные данные не нужны.**')))
                if case['input']:
                    blocks.append(dict(type='console', data=dict(lines=[dict(type='input', text=line) for line in case['input'].splitlines()])))
                blocks.append(dict(type='text', data=dict(text='**Вывод программы:**')))
                blocks.append(dict(type='console', data=dict(lines=[dict(type='output', text=line) for line in case['expected_output'].splitlines()])))
            tasks.append(dict(title=f"Задание {index+1}: {item['title'].lower()}",
                              content=dict(version=1, layout='vertical', blocks=blocks),
                              starter_code=item['starter_code'],
                              time_limit_ms=1000, memory_limit_mb=128,
                              tests=[dict(**case, is_hidden=i >= 2, order=i) for i, case in enumerate(item['tests'])]))
        result.append(dict(title=group['title'], description=group['reminder'], tasks=tasks))
    return dict(title=SECTION_TITLE, description='Повтори изученное на самостоятельных задачах: от коротких упражнений до программ с несколькими правилами. В конце — практика на разные темы.', lessons=result)


def validate():
    from pydantic import TypeAdapter
    from app.schemas.steps.step_layout import StepContent

    adapter = TypeAdapter(StepContent)
    count = 0
    data = payload()
    assert len(data['lessons']) == 8
    for authored, group in zip(LESSONS, data['lessons']):
        assert 10 <= len(group['tasks']) <= 20
        assert len({t['title'] for t in group['tasks']}) == len(group['tasks'])
        for source, item in zip(authored['tasks'], group['tasks']):
            adapter.validate_python(item['content'])
            compile(item['starter_code'], '<starter>', 'exec')
            assert len(item['tests']) >= 3
            for case in item['tests']:
                process = subprocess.run([sys.executable, '-I', '-c', source['reference']],
                    input=case['input'], text=True, capture_output=True, timeout=3)
                assert process.returncode == 0, (group['title'], item['title'], process.stderr)
                actual = process.stdout.replace('\r\n', '\n').strip()
                expected = case['expected_output'].strip()
                assert actual == expected, (group['title'], item['title'], case['input'], repr(process.stdout), repr(case['expected_output']))
                count += 1
    print(f'Проверено: {len(data["lessons"])} уроков, {sum(len(g["tasks"]) for g in data["lessons"])} задач, {count} тестов.')
    return data


def export(data):
    (ROOT / 'section.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# '+SECTION_TITLE, '', data['description'], '']
    for lesson in data['lessons']:
        lines += ['## '+lesson['title'], '']
        for item in lesson['tasks']:
            for block in item['content']['blocks']:
                if block['type'] == 'text':
                    lines += [block['data']['text'], '']
                elif block['type'] == 'callout':
                    lines += ['> '+block['data']['content'], '']
                elif block['type'] == 'console':
                    lines += ['```text', '\n'.join(line['text'] for line in block['data']['lines']), '```', '']
            if item['starter_code'] != '# Напиши программу здесь\n':
                lines += ['**Заготовка:**', '', '```python', item['starter_code'].rstrip(), '```', '']
    (ROOT / 'materials.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Экспортированы section.json и materials.md (без решений).')


async def apply(data, course_id):
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, engine
    from app.models import Course, Section, Lesson, Step, Task, TestCase
    try:
        async with AsyncSessionLocal() as session, session.begin():
            course = await session.get(Course, course_id)
            if course is None:
                raise ValueError('Курс не найден')
            sections = (await session.scalars(select(Section).where(
                Section.course_id == course_id, Section.title == SECTION_TITLE).with_for_update())).all()
            if len(sections) != 1:
                raise ValueError('Ожидалась ровно одна существующая секция с нужным названием')
            section = sections[0]
            existing = (await session.scalars(select(Lesson).where(Lesson.section_id == section.id).order_by(Lesson.order))).all()
            if existing:
                # Повторный запуск безопасен только при полном совпадении всех полей.
                assert len(existing) == len(data['lessons']), 'Секция уже содержит другие уроки'
                assert section.description == data['description'], 'Описание секции изменено'
                for order, (saved, authored) in enumerate(zip(existing, data['lessons'])):
                    assert (saved.title, saved.description, saved.order) == (authored['title'], authored['description'], order), 'Урок изменен'
                    steps = (await session.scalars(select(Step).where(Step.lesson_id == saved.id).order_by(Step.order))).all()
                    assert len(steps) == len(authored['tasks']), 'Количество степов изменено'
                    for step_order, (step, source) in enumerate(zip(steps, authored['tasks'])):
                        assert (step.title, step.content, step.order) == (source['title'], source['content'], step_order), 'Степ изменен'
                        task = await session.scalar(select(Task).where(Task.step_id == step.id))
                        assert task is not None, 'Нет задачи'
                        assert (task.starter_code, task.time_limit_ms, task.memory_limit_mb) == (source['starter_code'], source['time_limit_ms'], source['memory_limit_mb']), 'Задача изменена'
                        tests = (await session.scalars(select(TestCase).where(TestCase.task_id == task.id).order_by(TestCase.order))).all()
                        assert [dict(input=t.input, expected_output=t.expected_output, is_hidden=t.is_hidden, order=t.order) for t in tests] == source['tests'], 'Тесты изменены'
                print(f'Секция {section.id} уже содержит эти материалы. Совпадение проверено, изменений нет.')
                return
            section.description = data['description']
            for order, source in enumerate(data['lessons']):
                lesson = Lesson(section_id=section.id, title=source['title'], description=source['description'], order=order)
                session.add(lesson)
                await session.flush()
                for step_order, item in enumerate(source['tasks']):
                    step = Step(lesson_id=lesson.id, title=item['title'], order=step_order, content=item['content'])
                    session.add(step)
                    await session.flush()
                    task = Task(step_id=step.id, starter_code=item['starter_code'], time_limit_ms=item['time_limit_ms'], memory_limit_mb=item['memory_limit_mb'])
                    session.add(task)
                    await session.flush()
                    session.add_all(TestCase(task_id=task.id, **case) for case in item['tests'])
            await session.flush()
            print(f'Добавлено в курс «{course.title}», секция {section.id}: 8 уроков, 85 задач.')
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--export', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--course-id', type=int)
    args = parser.parse_args()
    if args.apply and args.course_id is None:
        parser.error('--apply требует явный --course-id')
    data = validate()
    if args.export:
        export(data)
    if args.apply:
        asyncio.run(apply(data, args.course_id))


if __name__ == '__main__':
    main()
