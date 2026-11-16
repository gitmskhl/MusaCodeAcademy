"""Проверка, экспорт и бережное добавление практики в базовый раздел Pygame."""
import argparse
import asyncio
import json
from pathlib import Path

from data.pygame_intro.content import SECTION_TITLE, LESSON as INTRO
from data.pygame_drawing.content import LESSON as DRAWING
from data.pygame_movement.content import LESSON as MOVEMENT
from data.pygame_keyboard.content import LESSON as KEYBOARD
from .content import IMAGES
from .illustrations import illustrated_lesson

ROOT = Path(__file__).resolve().parent
COURSE_SLUG = 'python-gamedev-basics'


def validate():
    from app.schemas.steps.step import StepCreate
    from PIL import Image

    lesson = illustrated_lesson()
    titles = set()
    examples = 0
    for item in lesson['steps']:
        StepCreate.model_validate(item)
        if item['title'] in titles:
            raise ValueError('Повтор названия степа')
        titles.add(item['title'])
        for block in item['content']['blocks']:
            if block['type'] == 'code':
                compile(block['data']['code'], item['title'], 'exec')
                examples += 1
    for number, filename, _ in IMAGES:
        assert 1 <= number <= len(lesson['steps'])
        path = ROOT / 'images' / filename
        with Image.open(path) as image:
            assert image.format == 'GIF' and image.is_animated
            for frame in range(image.n_frames):
                image.seek(frame)
                image.load()
        assert path.stat().st_size < 10 * 1024 * 1024
    print(f'Проверены {len(titles)} степов, {examples} примера и {len(IMAGES)} GIF.')


def export():
    lesson = illustrated_lesson()
    (ROOT / 'lesson.json').write_text(json.dumps(lesson, ensure_ascii=False, indent=2) + '\n')
    lines = ['# Урок 5. ' + lesson['title'], '', lesson['description'], '']
    for number, item in enumerate(lesson['steps'], 1):
        lines += [f'## Степ {number}. {item["title"]}', '']
        images_added = False
        for block in item['content']['blocks']:
            data = block['data']
            if block['type'] == 'text' and data['text'].startswith('### Подсказка'):
                for step_number, filename, caption in IMAGES:
                    if step_number == number:
                        lines += [f'![{caption}](images/{filename})', '', caption, '']
                images_added = True
            if block['type'] == 'text':
                lines += [data['text'], '']
            elif block['type'] == 'code':
                lines += ['```python', data['code'].rstrip(), '```', '']
            elif block['type'] == 'callout':
                lines += [f'> **{data["title"]}**', '>', '> ' + data['content'], '']
        for step_number, filename, caption in IMAGES:
            if step_number == number and not images_added:
                lines += [f'![{caption}](images/{filename})', '', caption, '']
    (ROOT / 'materials.md').write_text('\n'.join(lines))


async def apply(course_id):
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, engine
    from app.models import Course, Lesson, Section, Step

    desired = illustrated_lesson()
    result = None
    try:
        async with AsyncSessionLocal() as session, session.begin():
            course = await session.scalar(select(Course).where(Course.id == course_id).with_for_update())
            if course is None or course.slug != COURSE_SLUG:
                raise ValueError('Нужен курс с slug ' + COURSE_SLUG)
            section = await session.scalar(select(Section).where(
                Section.course_id == course_id, Section.title == SECTION_TITLE))
            if section is None:
                raise ValueError('Раздел базового Pygame не найден')
            lessons = (await session.scalars(select(Lesson).where(
                Lesson.section_id == section.id).order_by(Lesson.order))).all()
            prerequisites = [INTRO, DRAWING, MOVEMENT, KEYBOARD]
            if [(x.order, x.title) for x in lessons[:4]] != [(i, x['title']) for i, x in enumerate(prerequisites)]:
                raise ValueError('Ожидаются четыре предыдущих урока в исходном порядке')
            existing = [x for x in lessons if x.order == 4 or x.title == desired['title']]
            if existing:
                if len(existing) != 1:
                    raise ValueError('Позиция или название урока уже заняты')
                lesson = existing[0]
                if (lesson.order, lesson.title, lesson.description) != (4, desired['title'], desired['description']):
                    raise ValueError('Урок отличается; перезапись остановлена')
                steps = (await session.scalars(select(Step).where(
                    Step.lesson_id == lesson.id).order_by(Step.order))).all()
                if [(s.title, s.order, s.content) for s in steps] != [
                        (s['title'], i, s['content']) for i, s in enumerate(desired['steps'])]:
                    raise ValueError('Степы отличаются; перезапись остановлена')
                print(f'Урок {lesson.id}: все {len(steps)} степов совпадают, изменений нет.')
            else:
                if len(lessons) != 4:
                    raise ValueError('В разделе уже есть другие уроки; добавление остановлено')
                lesson = Lesson(section_id=section.id, title=desired['title'], description=desired['description'], order=4)
                session.add(lesson)
                await session.flush()
                steps = [Step(lesson_id=lesson.id, order=i, **s) for i, s in enumerate(desired['steps'])]
                session.add_all(steps)
                await session.flush()
                print(f'Курс {course.id}, раздел {section.id}, урок {lesson.id}: добавлено {len(steps)} степов.')
            result = {'course_id': course.id, 'section_id': section.id, 'lesson_id': lesson.id,
                      'slug': course.slug, 'steps': [{'id': s.id, 'title': s.title, 'order': s.order} for s in steps]}
        (ROOT / 'import-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
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
    if args.export:
        export()
    if args.apply:
        asyncio.run(apply(args.course_id))
