"""Проверка, экспорт и осторожное добавление секции в существующий курс.

Из корня проекта:
  python -m data.reinforcement.build --check
  python -m data.reinforcement.build --export
  python -m data.reinforcement.build --apply --course-id 1
"""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path

from .content import LESSONS
from .examples import checked_example, public_examples

SECTION_TITLE = 'Закрепление пройденного материала'
ROOT = Path(__file__).resolve().parent


def payload():
    result = []
    for group in LESSONS:
        tasks = []
        for index, item in enumerate(group['tasks']):
            blocks = [dict(type='text', data=dict(text=f"### {item['title']}\n\n{item['text']}"))]
            if index == 0:
                blocks.append(dict(type='callout', data=dict(
                    variant='tip', title='Вспомни', content=group['reminder'])))
            blocks.append(dict(type='text', data=dict(text='**Пример работы программы:**\n\nПосле знака `❯` показан ввод пользователя. Остальные строки выводит программа. Сообщения программы должны совпадать с примерами.')))
            for number, case in enumerate(public_examples(item)):
                if number:
                    blocks.append(dict(type='text', data=dict(text='**Ещё пример:**')))
                lines = checked_example(item['reference'], case)
                blocks.append(dict(type='console', data=dict(lines=lines)))
                inputs = [line['text'] for line in lines if line['type'] == 'input']
                notes = []
                if '' in inputs:
                    notes.append('Пустая строка после `❯` означает, что пользователь сразу нажал Enter.')
                if any(value and value.isspace() for value in inputs):
                    notes.append('В этом примере есть ввод из одних пробелов — это тоже строка текста.')
                if notes:
                    blocks.append(dict(type='text', data=dict(text=' '.join(notes))))
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
                checked_example(source['reference'], case)
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
                    transcript = []
                    for line in block['data']['lines']:
                        value = line['text']
                        if line['type'] == 'input':
                            if value == '':
                                value = '(пустая строка: Enter)'
                            elif value.isspace():
                                value = f'(только пробелы: {len(value)})'
                            transcript.append('❯ ' + value)
                        else:
                            transcript.append(value)
                    lines += ['```text', '\n'.join(transcript), '```', '']
            if item['starter_code'] != '# Напиши программу здесь\n':
                lines += ['**Заготовка:**', '', '```python', item['starter_code'].rstrip(), '```', '']
    (ROOT / 'materials.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Экспортированы section.json и materials.md (без решений).')


async def apply(data, course_id, wording_baseline=None):
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
                baseline = None
                if wording_baseline is not None:
                    baseline = {row['step_id']: row['content'] for row in json.loads(Path(wording_baseline).read_text(encoding='utf-8'))}
                changes = []
                # Повторный запуск безопасен только при полном совпадении всех полей.
                assert len(existing) == len(data['lessons']), 'Секция уже содержит другие уроки'
                assert section.description == data['description'], 'Описание секции изменено'
                for order, (saved, authored) in enumerate(zip(existing, data['lessons'])):
                    assert (saved.title, saved.description, saved.order) == (authored['title'], authored['description'], order), 'Урок изменен'
                    steps = (await session.scalars(select(Step).where(Step.lesson_id == saved.id).order_by(Step.order).with_for_update())).all()
                    assert len(steps) == len(authored['tasks']), 'Количество степов изменено'
                    for step_order, (step, source) in enumerate(zip(steps, authored['tasks'])):
                        assert (step.title, step.order) == (source['title'], step_order), 'Степ изменен'
                        if step.content != source['content']:
                            if baseline is None or step.content != baseline.get(step.id):
                                raise ValueError(f'Степ {step.id} отличается от ожидаемой исходной версии')
                            changes.append((step, source['content']))
                        task = await session.scalar(select(Task).where(Task.step_id == step.id).with_for_update())
                        assert task is not None, 'Нет задачи'
                        assert (task.starter_code, task.time_limit_ms, task.memory_limit_mb) == (source['starter_code'], source['time_limit_ms'], source['memory_limit_mb']), 'Задача изменена'
                        tests = (await session.scalars(select(TestCase).where(TestCase.task_id == task.id).order_by(TestCase.order).with_for_update())).all()
                        assert [dict(input=t.input, expected_output=t.expected_output, is_hidden=t.is_hidden, order=t.order) for t in tests] == source['tests'], 'Тесты изменены'
                if changes:
                    backup_root = ROOT.parents[1] / 'backups' / 'reinforcement_wording'
                    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
                    backup = backup_root / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
                    backup.write_text(json.dumps([dict(step_id=step.id, content=step.content) for step, _ in changes], ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                    backup.chmod(0o600)
                    for step, content in changes:
                        step.content = content
                    await session.flush()
                    print(f'Обновлены условия и примеры {len(changes)} задач. Копия: {backup}')
                else:
                    print(f'Секция {section.id} уже содержит эти материалы. Совпадение проверено, изменений нет.')
                return
            if wording_baseline is not None:
                raise ValueError('Обновление формулировок требует существующих задач')
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
    parser.add_argument('--wording-baseline', type=Path, help='Снимок исходных степов: разрешает обновление только их условий и примеров')
    args = parser.parse_args()
    if args.apply and args.course_id is None:
        parser.error('--apply требует явный --course-id')
    if args.wording_baseline is not None and not args.apply:
        parser.error('--wording-baseline используется только вместе с --apply')
    data = validate()
    if args.export:
        export(data)
    if args.apply:
        asyncio.run(apply(data, args.course_id, wording_baseline=args.wording_baseline))


if __name__ == '__main__':
    main()
