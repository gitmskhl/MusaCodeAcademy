"""Проверка, экспорт и добавление третьего урока в существующий раздел Pygame."""
import argparse
import asyncio
import json
from pathlib import Path

from data.pygame_intro.content import LESSON as FIRST_LESSON, SECTION_TITLE
from data.pygame_drawing.content import LESSON as SECOND_LESSON
from .content import IMAGES
from .illustrations import illustrated_lesson

ROOT = Path(__file__).resolve().parent
COURSE_SLUG = "python-gamedev-basics"


def validate():
    from app.schemas.steps.step import StepCreate

    lesson = illustrated_lesson()
    titles = set()
    examples = 0
    for item in lesson["steps"]:
        StepCreate.model_validate(item)
        if item["title"] in titles:
            raise ValueError("Повторяющееся название степа")
        titles.add(item["title"])
        for block in item["content"]["blocks"]:
            if block["type"] == "code":
                compile(block["data"]["code"], item["title"], "exec")
                examples += 1
    from PIL import Image
    for number, filename, _ in IMAGES:
        if not 1 <= number <= len(lesson["steps"]) or not (ROOT / "images" / filename).is_file():
            raise ValueError("Не найдено изображение: " + filename)
        path = ROOT / "images" / filename
        with Image.open(path) as image:
            if image.format != "GIF" or not image.is_animated or image.n_frames < 2:
                raise ValueError("Нужен анимированный GIF: " + filename)
            for frame in range(image.n_frames):
                image.seek(frame)
                image.load()
        if path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("GIF превышает лимит загрузки")
    print(f"Проверены схемы {len(titles)} степов, синтаксис {examples} примеров и {len(IMAGES)} изображений.")


def export():
    lesson = illustrated_lesson()
    (ROOT / "lesson.json").write_text(json.dumps(lesson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Урок 3. " + lesson["title"], "", lesson["description"], ""]
    for number, item in enumerate(lesson["steps"], 1):
        lines.extend([f"## Степ {number}. {item['title']}", ""])
        for block in item["content"]["blocks"]:
            data = block["data"]
            if block["type"] == "text":
                lines.extend([data["text"], ""])
            elif block["type"] == "code":
                lines.extend(["```python", data["code"].rstrip(), "```", ""])
            elif block["type"] == "callout":
                lines.extend([f"> **{data['title']}**", ">", "> " + data["content"], ""])
            # Изображения ниже добавляются по исходному каталогу, даже до загрузки в БД.
        for step_number, filename, caption in IMAGES:
            if step_number == number:
                lines.extend([f"![{caption}](images/{filename})", "", caption, ""])
    (ROOT / "materials.md").write_text("\n".join(lines), encoding="utf-8")


async def apply(course_id):
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, engine
    from app.models import Course, Lesson, Section, Step

    lesson_data = illustrated_lesson()
    try:
        async with AsyncSessionLocal() as session, session.begin():
            course = await session.scalar(select(Course).where(Course.id == course_id).with_for_update())
            if course is None or course.slug != COURSE_SLUG:
                raise ValueError("Нужен курс с slug " + COURSE_SLUG)
            section = await session.scalar(select(Section).where(
                Section.course_id == course_id, Section.title == SECTION_TITLE))
            if section is None:
                raise ValueError("Сначала добавьте первый урок: раздел Pygame не найден")
            lessons = (await session.scalars(select(Lesson).where(
                Lesson.section_id == section.id).order_by(Lesson.order))).all()
            if not lessons or lessons[0].title != FIRST_LESSON["title"] or lessons[0].order != 0:
                raise ValueError("Первый урок раздела отличается от ожидаемого")
            if len(lessons) < 2 or lessons[1].title != SECOND_LESSON["title"] or lessons[1].order != 1:
                raise ValueError("Сначала добавьте второй урок рисования")
            existing = [item for item in lessons if item.order == 2 or item.title == lesson_data["title"]]
            if existing:
                if len(existing) != 1:
                    raise ValueError("Позиция или название третьего урока уже заняты")
                lesson = existing[0]
                if (lesson.title, lesson.description, lesson.order) != (
                        lesson_data["title"], lesson_data["description"], 2):
                    raise ValueError("Третий урок отличается; перезапись не выполняется")
                steps = (await session.scalars(select(Step).where(
                    Step.lesson_id == lesson.id).order_by(Step.order))).all()
                expected = [(item["title"], order, item["content"])
                            for order, item in enumerate(lesson_data["steps"])]
                if [(item.title, item.order, item.content) for item in steps] != expected:
                    raise ValueError("Существующие степы отличаются; перезапись не выполняется")
                print(f"Урок {lesson.id}: все {len(steps)} степов совпадают, изменений нет.")
                return
            lesson = Lesson(section_id=section.id, title=lesson_data["title"],
                            description=lesson_data["description"], order=2)
            session.add(lesson)
            await session.flush()
            session.add_all(Step(lesson_id=lesson.id, order=order, **item)
                            for order, item in enumerate(lesson_data["steps"]))
            await session.flush()
            print(f"Курс {course_id}, раздел {section.id}, урок {lesson.id}: добавлено {len(lesson_data['steps'])} степов.")
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--course-id", type=int)
    args = parser.parse_args()
    if args.apply and args.course_id is None:
        parser.error("--apply требует --course-id")
    validate()
    if args.export:
        export()
    if args.apply:
        asyncio.run(apply(args.course_id))


if __name__ == "__main__":
    main()
