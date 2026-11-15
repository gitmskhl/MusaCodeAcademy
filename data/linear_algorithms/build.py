"""Проверка и добавление раздела без изменения прежних материалов курса."""
import argparse
import ast
import asyncio
import json
import os
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.models import Course, Lesson, Section, Step, Task, TestCase
from app.schemas.steps.step_layout import StepContent
from app.schemas.task import TaskCreate
from app.schemas.testCase import TestCaseCreate
from data.reinforcement.examples import checked_example
from .content import DESCRIPTION, LESSONS, TITLE, callout, text

ROOT = Path(__file__).resolve().parent
SLUG = 'python-basics-practice'
TASK_FIELDS = ('starter_code', 'checking_mode', 'time_limit_ms', 'memory_limit_mb')
TEST_FIELDS = ('input', 'expected_output', 'is_hidden', 'order')


def payload():
    lessons = []
    for group in LESSONS:
        steps = []
        for position, source in enumerate(group['steps']):
            if source['kind'] == 'theory':
                blocks = [callout('info', 'Перед практикой', group['description']), text(source['explanation'])]
                for i, example in enumerate(source['examples'], 1):
                    blocks += [text(f'### Пример алгоритма {i}'),
                        {'type': 'code', 'data': {'language': 'python', 'code': example['code']}},
                        text('**Вывод программы:**'), {'type': 'console', 'data': {'lines': [
                            {'type': 'output', 'text': line} for line in example['output'].splitlines()]}}]
                blocks += [text(source['walkthrough']), callout('warning', 'Частая ошибка', source['warning']),
                           callout('tip', 'Проверь себя', source['question'])]
                spec, tests = None, []
            else:
                blocks = [text(source['statement'])]
                tests = []
                for i, case in enumerate(source['tests']):
                    lines = checked_example(source['reference'], case)
                    if i < 2:
                        blocks += [text(f'### Пример работы {i+1}'), {'type': 'console', 'data': {'lines': lines}}]
                        if any(line['type'] == 'input' and not line['text'] for line in lines):
                            blocks.append(text('Пустая строка после `❯` означает, что пользователь сразу нажал Enter.'))
                    tests.append({**case, 'is_hidden': i >= 2, 'order': i})
                spec = dict(starter_code='# Напиши программу здесь\n', checking_mode='local',
                            time_limit_ms=1000, memory_limit_mb=128)
            steps.append(dict(title=source['title'], order=position, content={
                'version': 1, 'layout': 'vertical', 'blocks': blocks}, task=spec, tests=tests))
        lessons.append(dict(title=group['title'], description=group['description'], order=len(lessons), steps=steps))
    return dict(title=TITLE, description=DESCRIPTION, lessons=lessons)


def check_code(source):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            raise ValueError('В примерах должны использоваться обычные циклы')
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {'min', 'max', 'sum', 'sorted'}:
                raise ValueError('Эталон подменяет алгоритм встроенной функцией')
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'sort':
                raise ValueError('Сортировка вместо линейного алгоритма')


def validate():
    adapter = TypeAdapter(StepContent)
    data = payload()
    if len(LESSONS) != 5:
        raise ValueError('Ожидалось пять уроков')
    tests, snippets, sources = 0, 0, []
    for group, lesson in zip(LESSONS, data['lessons'], strict=True):
        if len(group['steps']) != 5 or group['steps'][0]['kind'] != 'theory':
            raise ValueError('Нужны первый теоретический степ и четыре задачи')
        for source, step in zip(group['steps'], lesson['steps'], strict=True):
            adapter.validate_python(step['content'])
            if step['task'] is None:
                if step['tests']:
                    raise ValueError('У теории не должно быть тестов')
                for example in source['examples']:
                    check_code(example['code'])
                    checked_example(example['code'], dict(input='', expected_output=example['output']))
                    snippets += 1
            else:
                TaskCreate.model_validate({'step_id': 1, **step['task']})
                check_code(source['reference'])
                if len(step['tests']) < 6 or len({t['input'] for t in step['tests']}) != len(step['tests']):
                    raise ValueError('Нужно хотя бы шесть различных проверочных входов')
                for case in step['tests']:
                    TestCaseCreate.model_validate({'task_id': 1, **case})
                    checked_example(source['reference'], case)
                    tests += 1
                if source['source']:
                    sources.append(source['source'])
    if len(sources) != 6 or len(set(sources)) != 6:
        raise ValueError('Должны быть представлены все шесть задач PDF')
    print(f'Проверено: 5 уроков, 5 теоретических степов, 20 задач, {tests} тестов, {snippets} примеров кода.')
    return data


def export(data):
    (ROOT/'section.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# '+TITLE, '', DESCRIPTION, '']
    mapping = []
    for group, lesson in zip(LESSONS, data['lessons'], strict=True):
        lines += ['## '+lesson['title'], '', lesson['description'], '']
        for source, step in zip(group['steps'], lesson['steps'], strict=True):
            lines += ['### '+step['title'], '']
            for block in step['content']['blocks']:
                value = block['data']
                if block['type'] == 'text':
                    lines += [value['text'], '']
                elif block['type'] == 'callout':
                    lines += ['**'+value['title']+'**', '', value['content'], '']
                elif block['type'] == 'code':
                    lines += ['```python', value['code'].rstrip(), '```', '']
                elif block['type'] == 'console':
                    lines += ['```text', '\n'.join(('❯ ' if line['type'] == 'input' else '')+line['text']
                                                  for line in value['lines']), '```', '']
            if source.get('source'):
                mapping.append(dict(source=source['source'], lesson=lesson['title'], task=step['title']))
    (ROOT/'materials.md').write_text('\n'.join(lines), encoding='utf-8')
    (ROOT/'source-mapping.json').write_text(json.dumps(mapping, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def graph(section):
    return dict(title=section.title, description=section.description, lessons=[dict(
        title=l.title, description=l.description, order=l.order, steps=[dict(
            title=s.title, order=s.order, content=s.content,
            task=None if s.task is None else {f: getattr(s.task, f) for f in TASK_FIELDS},
            tests=[] if s.task is None else [{f: getattr(t, f) for f in TEST_FIELDS}
                for t in sorted(s.task.test_cases, key=lambda t: (t.order, t.id))])
        for s in sorted(l.steps, key=lambda s: (s.order, s.id))])
        for l in sorted(section.lessons, key=lambda l: (l.order, l.id))])


def identifiers(section):
    return dict(section_id=section.id, lessons=[dict(lesson_id=l.id, title=l.title, steps=[dict(
        step_id=s.id, title=s.title, task_id=None if s.task is None else s.task.id)
        for s in sorted(l.steps, key=lambda s: (s.order, s.id))])
        for l in sorted(section.lessons, key=lambda l: (l.order, l.id))])


async def import_section(db, data, course_id):
    """Одна транзакция; существующий раздел допускает только полное совпадение."""
    async with db.begin():
        course = await db.scalar(select(Course).where(Course.id == course_id).with_for_update())
        if course is None or course.slug != SLUG:
            raise ValueError('Нужен существующий курс python-basics-practice')
        options = selectinload(Section.lessons).selectinload(Lesson.steps).selectinload(Step.task).selectinload(Task.test_cases)
        existing = (await db.scalars(select(Section).where(
            Section.course_id == course_id, Section.title == TITLE).options(options))).all()
        if len(existing) > 1:
            raise ValueError('Найдено несколько разделов с одинаковым названием')
        if existing:
            section = existing[0]
            if graph(section) != data:
                raise ValueError('Раздел отличается: запись отменена, ручные правки сохранены')
            status = 'unchanged'
        else:
            last = await db.scalar(select(func.max(Section.order)).where(Section.course_id == course_id))
            section = Section(course_id=course_id, title=data['title'], description=data['description'],
                              order=0 if last is None else last+1, lessons=[])
            for group in data['lessons']:
                lesson = Lesson(title=group['title'], description=group['description'], order=group['order'], steps=[])
                section.lessons.append(lesson)
                for spec in group['steps']:
                    step = Step(title=spec['title'], order=spec['order'], content=spec['content'], task=None)
                    lesson.steps.append(step)
                    if spec['task'] is not None:
                        step.task = Task(**spec['task'], test_cases=[TestCase(**case) for case in spec['tests']])
            db.add(section)
            await db.flush()
            status = 'created'
        result = dict(status=status, course_id=course.id, course_slug=course.slug,
                      is_published=course.is_published, **identifiers(section))
    return result


async def apply(data, url, course_id):
    engine = create_async_engine(url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            return await import_section(db, data, course_id)
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--export', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--course-id', type=int)
    parser.add_argument('--database-url-env', help='Имя переменной среды с явно выбранным URL базы')
    args = parser.parse_args()
    if args.apply and (args.course_id is None or not args.database_url_env or not os.environ.get(args.database_url_env)):
        parser.error('--apply требует --course-id и --database-url-env с непустой переменной среды')
    data = validate()
    if args.export:
        export(data)
    if args.apply:
        print(json.dumps(asyncio.run(apply(data, os.environ[args.database_url_env], args.course_id)), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
