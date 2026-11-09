"""Проверка, экспорт и загрузка авторского раздела «Словари»."""
import argparse
import ast
import asyncio
import json
from pathlib import Path
import subprocess
import sys

from .content import LESSONS

TITLE = 'Словари'
DESCRIPTION = 'Ключи и значения, добавление и удаление записей, проверка наличия ключа, обычный перебор и две системы учета оценок.'
ROOT = Path(__file__).resolve().parent


def text(value):
    return dict(type='text', data=dict(text=value))


def console(value, kind='output'):
    return dict(type='console', data=dict(lines=[dict(type=kind, text=line) for line in value.splitlines()]))


def payload():
    lessons = []
    for group in LESSONS:
        steps, task_index = [], 0
        for source in group['steps']:
            blocks = [text(source['text'])]
            item = dict(title=source['title'])
            if source['kind'] == 'theory':
                if source['code']:
                    blocks.append(dict(type='browser_python', data=dict(code=source['code'], stdin=source['stdin'])))
                    blocks += [text('**Вывод программы:**'), console(source['output'])]
            else:
                task_index += 1
                level = 'Базовая' if task_index <= 3 else 'Средняя' if task_index <= 7 else 'Повышенная'
                blocks.insert(0, text(f'### Задание {task_index}: {source["title"].lower()}\n\nСложность: **{level}**.'))
                if source['instructions']:
                    blocks.append(text('**Порядок ввода:**\n\n'+source['instructions']))
                for i, case in enumerate(source['tests'][:2], 1):
                    blocks.append(text(f'**Пример {i}. Ввод:**' if case['input'] else f'**Пример {i}. Ввод не нужен.**'))
                    if case['input']:
                        blocks.append(console(case['input'], 'input'))
                    blocks.extend([text('**Вывод программы:**'), console(case['expected_output'])])
                item.update(title=f'Задание {task_index}: {source["title"].lower()}', task=dict(
                    starter_code=source['starter_code'], time_limit_ms=1000, memory_limit_mb=128,
                    tests=[dict(**case, is_hidden=i >= 2, order=i) for i, case in enumerate(source['tests'])]))
            item['content'] = dict(version=1, layout='vertical', blocks=blocks)
            steps.append(item)
        lessons.append(dict(title=group['title'], description=group['description'], steps=steps))
    return dict(title=TITLE, description=DESCRIPTION, lessons=lessons)


def run_case(code, stdin, expected, label):
    tree = ast.parse(code)
    banned = {'items', 'values', 'keys', 'get', 'setdefault', 'update', 'pop', 'popitem'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in banned:
            raise ValueError(f'{label}: использован метод {node.attr}')
        if isinstance(node, (ast.DictComp, ast.ListComp, ast.SetComp, ast.GeneratorExp)):
            raise ValueError(f'{label}: использована неизученная конструкция')
    result = subprocess.run([sys.executable, '-I', '-c', code], input=stdin,
        text=True, capture_output=True, timeout=3)
    if result.returncode != 0 or result.stdout.replace('\r\n','\n').strip() != expected.strip():
        raise ValueError((label, stdin, result.stdout, expected, result.stderr))


def validate():
    from pydantic import TypeAdapter
    from app.schemas.steps.step_layout import StepContent
    adapter = TypeAdapter(StepContent)
    data, tests, snippets = payload(), 0, 0
    if len(data['lessons']) != 7:
        raise ValueError('Ожидалось 7 уроков')
    for group, authored in zip(data['lessons'], LESSONS):
        tasks = [s for s in group['steps'] if 'task' in s]
        if len(tasks) != 10:
            raise ValueError('Ожидалось 10 задач в каждом уроке')
        if len({s['title'] for s in group['steps']}) != len(group['steps']):
            raise ValueError('Названия степов повторяются')
        for step, source in zip(group['steps'], authored['steps']):
            adapter.validate_python(step['content'])
            if 'task' in step:
                compile(step['task']['starter_code'], '<starter>', 'exec')
                if len(source['tests']) < (3 if any(c['input'] for c in source['tests']) else 1):
                    raise ValueError('Недостаточно проверочных сценариев')
                for case in source['tests']:
                    run_case(source['reference'], case['input'], case['expected_output'], step['title'])
                    tests += 1
            elif source['code']:
                run_case(source['code'], source['stdin'], source['output'], step['title'])
                snippets += 1
    print(f'Проверено: 7 уроков, 70 задач, {tests} тестов, {snippets} исполняемых примеров теории.')
    return data


def export(data):
    (ROOT/'section.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['# '+TITLE, '', DESCRIPTION, '']
    for lesson in data['lessons']:
        lines += ['## '+lesson['title'], '', lesson['description'], '']
        for step in lesson['steps']:
            lines += ['### '+step['title'], '']
            for block in step['content']['blocks']:
                if block['type'] == 'text':
                    lines += [block['data']['text'], '']
                elif block['type'] == 'console':
                    lines += ['```text', '\n'.join(l['text'] for l in block['data']['lines']), '```', '']
                elif block['type'] == 'browser_python':
                    lines += ['```python', block['data']['code'], '```', '']
                    if block['data']['stdin']:
                        lines += ['**Входные данные примера:**', '', '```text', block['data']['stdin'].rstrip('\n'), '```', '']
            if 'task' in step and step['task']['starter_code'] != '# Напиши программу здесь\n':
                lines += ['**Заготовка:**', '', '```python', step['task']['starter_code'].rstrip(), '```', '']
    (ROOT/'materials.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Сохранены section.json и materials.md без эталонных решений задач.')


def ensure_equal(actual, expected, message):
    if actual != expected:
        raise ValueError(message)


async def apply(data, course_id):
    from sqlalchemy import select, func
    from app.core.database import AsyncSessionLocal, engine
    from app.models import Course, Section, Lesson, Step, Task, TestCase
    try:
        async with AsyncSessionLocal() as session, session.begin():
            # Блокировка курса защищает также создание новой секции от параллельного импорта.
            course = await session.scalar(select(Course).where(Course.id == course_id).with_for_update())
            if course is None:
                raise ValueError('Курс не найден')
            sections = (await session.scalars(select(Section).where(Section.course_id == course_id, Section.title == TITLE))).all()
            if len(sections) > 1:
                raise ValueError('Найдено несколько секций с названием «Словари»')
            if sections:
                section = sections[0]
                ensure_equal(section.description, data['description'], 'Описание существующей секции отличается')
                lessons = (await session.scalars(select(Lesson).where(Lesson.section_id == section.id).order_by(Lesson.order))).all()
                ensure_equal(len(lessons), len(data['lessons']), 'Секция уже содержит другие уроки')
                for order, (saved, source) in enumerate(zip(lessons, data['lessons'])):
                    ensure_equal((saved.title, saved.description, saved.order), (source['title'], source['description'], order), 'Урок отличается')
                    steps = (await session.scalars(select(Step).where(Step.lesson_id == saved.id).order_by(Step.order))).all()
                    ensure_equal(len(steps), len(source['steps']), 'Количество степов отличается')
                    for position, (step, authored) in enumerate(zip(steps, source['steps'])):
                        ensure_equal((step.title, step.order, step.content), (authored['title'], position, authored['content']), 'Степ отличается')
                        task = await session.scalar(select(Task).where(Task.step_id == step.id))
                        if 'task' not in authored:
                            ensure_equal(task, None, 'У теоретического степа появилась задача')
                            continue
                        if task is None:
                            raise ValueError('Нет задачи у практического степа')
                        spec = authored['task']
                        ensure_equal((task.starter_code,task.time_limit_ms,task.memory_limit_mb), (spec['starter_code'],spec['time_limit_ms'],spec['memory_limit_mb']), 'Задача отличается')
                        cases = (await session.scalars(select(TestCase).where(TestCase.task_id == task.id).order_by(TestCase.order))).all()
                        ensure_equal([dict(input=t.input,expected_output=t.expected_output,is_hidden=t.is_hidden,order=t.order) for t in cases], spec['tests'], 'Тесты отличаются')
                print(f'Секция {section.id} уже загружена. Полное совпадение проверено, изменений нет.')
                return
            last = await session.scalar(select(func.max(Section.order)).where(Section.course_id == course_id))
            section = Section(course_id=course_id,title=TITLE,description=DESCRIPTION,order=0 if last is None else last+1)
            session.add(section)
            await session.flush()
            for order, source in enumerate(data['lessons']):
                lesson = Lesson(section_id=section.id,title=source['title'],description=source['description'],order=order)
                session.add(lesson)
                await session.flush()
                for position, authored in enumerate(source['steps']):
                    step = Step(lesson_id=lesson.id,title=authored['title'],order=position,content=authored['content'])
                    session.add(step)
                    await session.flush()
                    if 'task' in authored:
                        spec = authored['task']
                        task = Task(step_id=step.id,starter_code=spec['starter_code'],time_limit_ms=spec['time_limit_ms'],memory_limit_mb=spec['memory_limit_mb'])
                        session.add(task)
                        await session.flush()
                        session.add_all(TestCase(task_id=task.id,**case) for case in spec['tests'])
            await session.flush()
            print(f'Добавлен раздел «{TITLE}» в курс «{course.title}»: секция {section.id}, 7 уроков, 70 задач.')
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--export',action='store_true')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--course-id',type=int)
    args = parser.parse_args()
    if args.apply and args.course_id is None:
        parser.error('Для --apply укажи --course-id')
    data = validate()
    if args.export:
        export(data)
    if args.apply:
        asyncio.run(apply(data,args.course_id))


if __name__ == '__main__':
    main()
