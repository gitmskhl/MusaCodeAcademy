"""Проверка, экспорт и транзакционное добавление нового раздела Pygame."""
import argparse
import asyncio
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from .content import SECTION, IMAGES

ROOT = Path(__file__).resolve().parent
SLUG = 'python-gamedev-basics'


def illustrated_section(manifest=None):
    section = deepcopy(SECTION)
    if manifest is None:
        path = ROOT / 'images.json'
        manifest = json.loads(path.read_text()) if path.exists() else {}
    for lesson_number, step_number, filename, caption in IMAGES:
        if filename not in manifest:
            continue
        blocks = section['lessons'][lesson_number-1]['steps'][step_number-1]['content']['blocks']
        position = next(i for i, b in enumerate(blocks) if b['type'] == 'text' and b['data']['text'].startswith('### Подсказка'))
        blocks.insert(position, {'type': 'image', 'data': {
            'file_id': manifest[filename]['file_id'], 'width': 100,
            'caption': caption + ' Плашка и крестик курсора поясняют демонстрацию; рисовать их в задании не нужно. При повторе GIF программа начинается заново.',
        }})
    return section


def validate():
    from app.schemas.steps.step import StepCreate
    from PIL import Image
    section = illustrated_section()
    count = examples = 0
    for lesson in section['lessons']:
        assert len(lesson['title']) <= 255
        assert len({s['title'] for s in lesson['steps']}) == len(lesson['steps'])
        for item in lesson['steps']:
            StepCreate.model_validate(item)
            count += 1
            for block in item['content']['blocks']:
                if block['type'] == 'code':
                    compile(block['data']['code'], item['title'], 'exec')
                    examples += 1
    for ln, sn, filename, _ in IMAGES:
        assert SECTION['lessons'][ln-1]['steps'][sn-1]['title'].startswith('Задание')
        path = ROOT / 'images' / filename
        with Image.open(path) as image:
            assert image.format == 'GIF' and image.is_animated
            assert image.size == (800, 680)
            for frame in range(image.n_frames):
                image.seek(frame)
                image.load()
        assert path.stat().st_size < 10 * 1024 * 1024
    assert sum(s['title'].startswith('Задание') for l in SECTION['lessons'] for s in l['steps']) == 9
    print(f'Проверены {len(section["lessons"])} уроков, {count} степа, {examples} блоков кода, {len(IMAGES)} GIF.')


def export():
    section = illustrated_section()
    (ROOT / 'section.json').write_text(json.dumps(section, ensure_ascii=False, indent=2) + '\n')
    lines = ['# ' + section['title'], '', section['description'], '']
    for ln, lesson in enumerate(section['lessons'], 1):
        lines += [f'## Урок {ln}. {lesson["title"]}', '', lesson['description'], '']
        for sn, item in enumerate(lesson['steps'], 1):
            lines += [f'### Степ {sn}. {item["title"]}', '']
            for block in item['content']['blocks']:
                data = block['data']
                if block['type'] == 'text' and data['text'].startswith('### Подсказка'):
                    for iln, isn, filename, caption in IMAGES:
                        if (iln, isn) == (ln, sn):
                            lines += [f'![{caption}](images/{filename})', '', caption + ' При повторе GIF программа начинается заново.', '']
                if block['type'] == 'text':
                    lines += [data['text'], '']
                elif block['type'] == 'code':
                    lines += ['```python', data['code'].rstrip(), '```', '']
                elif block['type'] == 'callout':
                    lines += [f'> **{data["title"]}**', '>', '> ' + data['content'], '']
    (ROOT / 'materials.md').write_text('\n'.join(lines))


async def snapshot(session, course_id, exclude=None):
    from sqlalchemy import select, inspect
    from app.models import Section, Lesson, Step
    sections = select(Section.id).where(Section.course_id == course_id)
    if exclude is not None:
        sections = sections.where(Section.id != exclude)
    lessons = select(Lesson.id).where(Lesson.section_id.in_(sections))
    result = {}
    for model, condition in [(Section, Section.id.in_(sections)), (Lesson, Lesson.id.in_(lessons)), (Step, Step.lesson_id.in_(lessons))]:
        rows = (await session.scalars(select(model).where(condition).order_by(model.id))).all()
        result[model.__tablename__] = [{c.key: getattr(row, c.key) for c in inspect(model).columns} for row in rows]
    return json.loads(json.dumps(result, default=str))


async def apply(course_id):
    from fastapi import UploadFile
    from starlette.datastructures import Headers
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, engine
    from app.models import Course, Section, Lesson, Step, File
    from app.services.storage import storage_service

    created_paths, manifest, committed = [], {}, False
    try:
        async with AsyncSessionLocal() as session, session.begin():
            course = await session.scalar(select(Course).where(Course.id == course_id).with_for_update())
            if course is None or course.slug != SLUG:
                raise ValueError('Нужен курс ' + SLUG)
            sections = (await session.scalars(select(Section).where(Section.course_id == course.id).order_by(Section.order))).all()
            if not sections or (sections[0].order, sections[0].title) != (0, 'Знакомство с Pygame'):
                raise ValueError('Не найден первый раздел курса')
            prerequisites = (await session.scalars(select(Lesson).where(Lesson.section_id == sections[0].id).order_by(Lesson.order))).all()
            if [(l.order, l.title) for l in prerequisites] != [
                (0, 'Первое окно и игровой цикл'), (1, 'Рисуем круги: координаты и снеговик'),
                (2, 'Движение: оживляем круг'), (3, 'Клавиатура: реагируем на нажатия'),
                (4, 'Практика: табло, светофор и управление движением')]:
                raise ValueError('Ожидаются пять предыдущих уроков; содержание уроков не перезаписывается')
            existing = [s for s in sections if s.title == SECTION['title'] or s.order == 1]
            if len(existing) > 1 or len(sections) != 1 + len(existing):
                raise ValueError('В курсе обнаружены другие разделы; добавление остановлено')
            target = existing[0] if existing else None
            before = await snapshot(session, course.id, target.id if target else None)
            backup = ROOT / 'before-import.json'
            if not backup.exists():
                backup.write_text(json.dumps(before, ensure_ascii=False, indent=2) + '\n')
            for _, _, filename, _ in IMAGES:
                source = ROOT / 'images' / filename
                digest = sha256(source.read_bytes()).hexdigest()
                original = 'pygame-objects-' + source.stem + '-' + digest[:16] + '.gif'
                file = await session.scalar(select(File).where(File.original_filename == original))
                if file is None:
                    with source.open('rb') as stream:
                        upload = UploadFile(file=stream, filename=original, headers=Headers({'content-type': 'image/gif'}))
                        stored = await storage_service.save_image(upload)
                    created_paths.append(stored.storage_path)
                    file = File(file_type=stored.file_type, original_filename=stored.original_filename,
                                storage_path=stored.storage_path, mime_type=stored.mime_type, size=stored.size)
                    session.add(file)
                    await session.flush()
                saved_path = storage_service.upload_dir / file.storage_path
                if not saved_path.is_file() or sha256(saved_path.read_bytes()).hexdigest() != digest:
                    raise ValueError('Содержимое загрузки отличается от GIF: ' + filename)
                manifest[filename] = {'file_id': file.id, 'storage_path': file.storage_path, 'sha256': digest}
            desired = illustrated_section(manifest)
            result = {'course_id': course.id, 'slug': course.slug, 'lessons': []}
            if target:
                if (target.order, target.title, target.description) != (1, desired['title'], desired['description']):
                    raise ValueError('Существующий раздел отличается; перезапись остановлена')
                saved_lessons = (await session.scalars(select(Lesson).where(Lesson.section_id == target.id).order_by(Lesson.order))).all()
                if len(saved_lessons) != len(desired['lessons']):
                    raise ValueError('Количество уроков отличается')
            else:
                target = Section(course_id=course.id, order=1, title=desired['title'], description=desired['description'])
                session.add(target)
                await session.flush()
                saved_lessons = []
            for i, source_lesson in enumerate(desired['lessons']):
                if saved_lessons:
                    lesson = saved_lessons[i]
                    if (lesson.order, lesson.title, lesson.description) != (i, source_lesson['title'], source_lesson['description']):
                        raise ValueError('Урок отличается; перезапись остановлена')
                    saved_steps = (await session.scalars(select(Step).where(Step.lesson_id == lesson.id).order_by(Step.order))).all()
                    if [(s.order, s.title, s.content) for s in saved_steps] != [(j, s['title'], s['content']) for j, s in enumerate(source_lesson['steps'])]:
                        raise ValueError('Степы отличаются; перезапись остановлена')
                else:
                    lesson = Lesson(section_id=target.id, order=i, title=source_lesson['title'], description=source_lesson['description'])
                    session.add(lesson)
                    await session.flush()
                    saved_steps = [Step(lesson_id=lesson.id, order=j, **s) for j, s in enumerate(source_lesson['steps'])]
                    session.add_all(saved_steps)
                    await session.flush()
                result['lessons'].append({'id': lesson.id, 'title': lesson.title, 'steps': [{'id': s.id, 'title': s.title} for s in saved_steps]})
            result['section_id'] = target.id
            after = await snapshot(session, course.id, target.id)
            if before != after:
                raise ValueError('Прежние материалы изменились; транзакция отменена')
            result['preserved'] = {k: len(v) for k, v in before.items()}
            result['action'] = 'verified' if existing else 'created'
        committed = True
        (ROOT / 'images.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        (ROOT / 'import-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
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
    parser.add_argument('--course-id', type=int)
    args = parser.parse_args()
    if args.apply and args.course_id is None:
        parser.error('--apply требует --course-id')
    validate()
    if args.apply:
        asyncio.run(apply(args.course_id))
    if args.export:
        export()
