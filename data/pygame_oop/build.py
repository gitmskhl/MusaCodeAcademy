"""Валидация, экспорт и добавление двух разделов ООП одной транзакцией."""
import argparse
import asyncio
import json
from pathlib import Path
from hashlib import sha256

from .content import SECTIONS, MAPPING, SOURCES, DEMOS, illustrated_sections

ROOT = Path(__file__).resolve().parent
SLUG = 'python-gamedev-basics'
PREREQUISITES = [(0, 'Знакомство с Pygame'), (1, 'Генерация множества объектов')]


def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def validate():
    from app.schemas.steps.step import StepCreate
    count = examples = 0
    tasks = []
    for section in illustrated_sections():
        assert len(section['title']) <= 255
        for lesson in section['lessons']:
            assert 0 < len(lesson['title']) <= 255
            assert len({s['title'] for s in lesson['steps']}) == len(lesson['steps'])
            for item in lesson['steps']:
                StepCreate.model_validate(item)
                count += 1
                if item['title'].startswith('Задание '):
                    tasks.append(item['title'])
                    values = [b['data'].get('text', '') for b in item['content']['blocks']]
                    for heading in ['### Что нужно сделать', '### Проверь себя', '### Подсказка']:
                        assert any(v.startswith(heading) for v in values), item['title']
                for block in item['content']['blocks']:
                    if block['type'] == 'code':
                        compile(block['data']['code'], item['title'], 'exec')
                        examples += 1
    assert len(tasks) == 16 and len(set(tasks)) == 16
    assert {m['version'] for m in MAPPING} == set(SOURCES)
    assert [m['task'] for m in MAPPING] == tasks
    assert set(DEMOS) == set(tasks)
    print(f'Проверены 2 раздела, 14 уроков, {count} степов, {examples} блоков кода и 16 заданий.')


def export():
    desired = illustrated_sections()
    write_json('sections.json', desired)
    write_json('source-mapping.json', MAPPING)
    lines = ['# ООП в разработке игр', '']
    for section in desired:
        lines += ['# ' + section['title'], '', section['description'], '']
        for lesson in section['lessons']:
            lines += ['## ' + lesson['title'], '', lesson['description'], '']
            for item in lesson['steps']:
                lines += ['### ' + item['title'], '']
                for block in item['content']['blocks']:
                    data = block['data']
                    if block['type'] == 'text':
                        lines += [data['text'], '']
                        if data['text'] == '### Что должно получиться':
                            lines += [f'![Пример результата](images/{DEMOS[item["title"]]})', '',
                                      'Белый указатель и плашка поясняют действия. При повторе начинаем заново.', '']
                    elif block['type'] == 'code':
                        lines += ['```python', data['code'].rstrip(), '```', '']
                    elif block['type'] == 'callout':
                        lines += ['> **' + data['title'] + '**', '> ' + data['content'], '']
    (ROOT / 'materials.md').write_text('\n'.join(lines))


async def snapshot(session, course_id, exclude=()):
    from sqlalchemy import select, inspect
    from app.models import Section, Lesson, Step
    section_ids = select(Section.id).where(Section.course_id == course_id)
    if exclude:
        section_ids = section_ids.where(Section.id.not_in(exclude))
    lesson_ids = select(Lesson.id).where(Lesson.section_id.in_(section_ids))
    result = {}
    for model, condition in [(Section, Section.id.in_(section_ids)),
                             (Lesson, Lesson.id.in_(lesson_ids)),
                             (Step, Step.lesson_id.in_(lesson_ids))]:
        rows = (await session.scalars(select(model).where(condition).order_by(model.id))).all()
        result[model.__tablename__] = [{c.key: getattr(row, c.key) for c in inspect(model).columns} for row in rows]
    return json.loads(json.dumps(result, default=str))


async def verify_section(session, target, desired, order):
    from sqlalchemy import select
    from app.models import Lesson, Step
    if (target.order, target.title, target.description) != (order, desired['title'], desired['description']):
        raise ValueError('Раздел отличается от экспорта: ' + desired['title'])
    lessons = (await session.scalars(select(Lesson).where(Lesson.section_id == target.id).order_by(Lesson.order))).all()
    if len(lessons) != len(desired['lessons']):
        raise ValueError('Количество уроков отличается: ' + target.title)
    result = []
    for i, (lesson, source) in enumerate(zip(lessons, desired['lessons'], strict=True)):
        if (lesson.order, lesson.title, lesson.description) != (i, source['title'], source['description']):
            raise ValueError('Урок отличается: ' + lesson.title)
        steps = (await session.scalars(select(Step).where(Step.lesson_id == lesson.id).order_by(Step.order))).all()
        if [(s.order, s.title, s.content) for s in steps] != [(j, s['title'], s['content']) for j, s in enumerate(source['steps'])]:
            raise ValueError('Степы отличаются: ' + lesson.title)
        result.append(dict(id=lesson.id, title=lesson.title, steps=[dict(id=s.id, title=s.title) for s in steps]))
    return dict(id=target.id, title=target.title, lessons=result)


async def upload_images(session, created_paths):
    from fastapi import UploadFile
    from starlette.datastructures import Headers
    from sqlalchemy import select
    from app.models import File
    from app.services.storage import storage_service
    from PIL import Image
    manifest = {}
    for filename in DEMOS.values():
        source = ROOT / 'images' / filename
        digest = sha256(source.read_bytes()).hexdigest()
        with Image.open(source) as gif:
            assert gif.format == 'GIF' and gif.is_animated and gif.size == (800, 680)
        original = 'pygame-oop-' + source.stem + '-' + digest[:16] + '.gif'
        file = await session.scalar(select(File).where(File.original_filename == original))
        if file is None:
            with source.open('rb') as stream:
                saved = await storage_service.save_image(UploadFile(file=stream, filename=original, headers=Headers({'content-type': 'image/gif'})))
            created_paths.append(saved.storage_path)
            file = File(file_type=saved.file_type, original_filename=saved.original_filename,
                        storage_path=saved.storage_path, mime_type=saved.mime_type, size=saved.size)
            session.add(file)
            await session.flush()
        assert sha256((storage_service.upload_dir / file.storage_path).read_bytes()).hexdigest() == digest
        manifest[filename] = dict(file_id=file.id, storage_path=file.storage_path, sha256=digest)
    return manifest


async def revise_section(session, target, desired):
    from sqlalchemy import select
    from app.models import Lesson, Step
    target.description = desired['description']
    lessons = (await session.scalars(select(Lesson).where(Lesson.section_id == target.id))).all()
    by_title = {l.title: l for l in lessons}
    for order, source in enumerate(desired['lessons']):
        lesson = by_title[source['title']]
        lesson.order, lesson.description = order, source['description']
        saved = (await session.scalars(select(Step).where(Step.lesson_id == lesson.id))).all()
        by_step_title = {s.title: s for s in saved}
        assert set(by_step_title) <= {s['title'] for s in source['steps']}
        for position, item in enumerate(source['steps']):
            row = by_step_title.get(item['title'])
            if row is None:
                session.add(Step(lesson_id=lesson.id, order=position, **item))
            else:
                row.order, row.content = position, item['content']
    await session.flush()


async def apply(course_id, revise=False):
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, engine
    from app.models import Course, Section, Lesson, Step
    from app.services.storage import storage_service
    created_paths, committed = [], False
    try:
        async with AsyncSessionLocal() as session, session.begin():
            course = await session.scalar(select(Course).where(Course.id == course_id).with_for_update())
            if course is None or course.slug != SLUG:
                raise ValueError('Нужен курс ' + SLUG)
            sections = (await session.scalars(select(Section).where(Section.course_id == course.id).order_by(Section.order))).all()
            previous = [s for s in sections if s.order < 2]
            if [(s.order, s.title) for s in previous] != PREREQUISITES:
                raise ValueError('Не найдены два предыдущих раздела курса')
            titles = {s['title'] for s in SECTIONS}
            targets = [s for s in sections if s.title in titles or s.order in (2, 3)]
            if len(targets) not in (0, 2):
                raise ValueError('Обнаружена частичная установка или конфликт порядка')
            if targets and [(s.order, s.title) for s in targets] != [(i + 2, s['title']) for i, s in enumerate(SECTIONS)]:
                raise ValueError('Обнаружен посторонний раздел на позиции ООП')
            if not targets and any(s.order >= 2 for s in sections):
                raise ValueError('После вводных разделов уже есть другие материалы; импорт остановлен')
            excluded = [s.id for s in targets]
            before = await snapshot(session, course.id, excluded)
            if not (ROOT / 'before-import.json').exists():
                write_json('before-import.json', before)
            manifest = await upload_images(session, created_paths)
            desired_sections = illustrated_sections(manifest)
            if targets and revise:
                baseline = json.loads((ROOT / 'revisions/v1-sections.json').read_text())
                for i, (target, desired, old) in enumerate(zip(targets, desired_sections, baseline, strict=True), 2):
                    try:
                        await verify_section(session, target, desired, i)
                    except ValueError:
                        # Обновлять можно только исходную версию, которую мы действительно читали.
                        await verify_section(session, target, old, i)
                backup = ROOT / 'revisions/before-school-update.json'
                if not backup.exists():
                    backup.write_text(json.dumps(await snapshot(session, course.id), ensure_ascii=False, indent=2) + '\n')
                for target, desired in zip(targets, desired_sections, strict=True):
                    await revise_section(session, target, desired)
            if not targets:
                for i, source in enumerate(desired_sections, 2):
                    target = Section(course_id=course.id, title=source['title'], description=source['description'], order=i)
                    session.add(target)
                    await session.flush()
                    targets.append(target)
                    for j, content in enumerate(source['lessons']):
                        lesson = Lesson(section_id=target.id, order=j, title=content['title'], description=content['description'])
                        session.add(lesson)
                        await session.flush()
                        session.add_all([Step(lesson_id=lesson.id, order=k, **item) for k, item in enumerate(content['steps'])])
                    await session.flush()
            result = dict(course_id=course.id, slug=course.slug, sections=[], action='revised' if revise and excluded else ('verified' if excluded else 'created'))
            for i, (target, desired) in enumerate(zip(targets, desired_sections, strict=True), 2):
                result['sections'].append(await verify_section(session, target, desired, i))
            after = await snapshot(session, course.id, [s.id for s in targets])
            if before != after:
                raise ValueError('Прежние материалы изменились; транзакция отменена')
            result['preserved'] = {k: len(v) for k, v in before.items()}
        committed = True
        # Читаем уже зафиксированные записи в новой сессии.
        async with AsyncSessionLocal() as session:
            for target_data, desired in zip(result['sections'], desired_sections, strict=True):
                target = await session.get(Section, target_data['id'])
                await verify_section(session, target, desired, 2 + result['sections'].index(target_data))
            assert await snapshot(session, course.id, [s['id'] for s in result['sections']]) == before
        write_json('import-result.json', result)
        write_json('images.json', manifest)
        print(json.dumps(result, ensure_ascii=False))
    except Exception:
        if not committed:
            for path in created_paths:
                await storage_service.delete(path)
        raise
    finally:
        await engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--export', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--revise', action='store_true')
    parser.add_argument('--course-id', type=int)
    args = parser.parse_args()
    if args.apply and args.course_id is None:
        parser.error('--apply требует --course-id')
    validate()
    if args.apply:
        asyncio.run(apply(args.course_id, revise=args.revise))
    if args.export:
        export()
