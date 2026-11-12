"""Проверка, экспорт и добавление первого урока в пустой курс разработки игр."""
import argparse
import asyncio
import json
from pathlib import Path

from .content import SECTION_DESCRIPTION, SECTION_TITLE
from .illustrations import IMAGES, illustrated_lesson

LESSON = illustrated_lesson()

ROOT = Path(__file__).resolve().parent
COURSE_SLUG = "python-gamedev-basics"


def validate():
    from app.schemas.steps.step import StepCreate

    titles = set()
    examples = 0
    for item in LESSON["steps"]:
        StepCreate.model_validate(item)
        if item["title"] in titles:
            raise ValueError("Повторяющееся название степа")
        titles.add(item["title"])
        for block in item["content"]["blocks"]:
            if block["type"] == "code":
                compile(block["data"]["code"], item["title"], "exec")
                examples += 1
    print(f"Проверены схемы {len(titles)} степов и синтаксис {examples} примеров.")


def export():
    data = {"title": SECTION_TITLE, "description": SECTION_DESCRIPTION, "lessons": [LESSON]}
    (ROOT / "section.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Урок 1. " + LESSON["title"], "", LESSON["description"], ""]
    for number, item in enumerate(LESSON["steps"], 1):
        lines.extend([f"## Степ {number}. {item['title']}", ""])
        for block in item["content"]["blocks"]:
            data = block["data"]
            if block["type"] == "text":
                lines.extend([data["text"], ""])
            elif block["type"] == "code":
                lines.extend(["```python", data["code"].rstrip(), "```", ""])
            elif block["type"] == "callout":
                lines.extend([f"> **{data['title']}**", ">", "> " + data["content"], ""])
            elif block["type"] == "image":
                filename = next(filename for step_number, filename, _ in IMAGES if step_number == number)
                lines.extend([f"![{data['caption']}](images/{filename})", "", data["caption"], ""])
    (ROOT / "materials.md").write_text("\n".join(lines), encoding="utf-8")


async def apply(course_id):
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal, engine
    from app.models import Course, Lesson, Section, Step

    try:
        async with AsyncSessionLocal() as session, session.begin():
            course = await session.scalar(select(Course).where(Course.id == course_id).with_for_update())
            if course is None or course.slug != COURSE_SLUG:
                raise ValueError("Нужен существующий курс разработки игр с slug " + COURSE_SLUG)
            sections = (await session.scalars(select(Section).where(Section.course_id == course_id).order_by(Section.order))).all()
            if sections:
                # Повторный запуск допускается только при полном совпадении материалов.
                if len(sections) != 1:
                    raise ValueError("Курс уже содержит другие разделы")
                section = sections[0]
                if (section.title, section.description, section.order) != (SECTION_TITLE, SECTION_DESCRIPTION, 0):
                    raise ValueError("Курс уже содержит другой раздел")
                lessons = (await session.scalars(select(Lesson).where(Lesson.section_id == section.id).order_by(Lesson.order))).all()
                if len(lessons) != 1:
                    raise ValueError("Раздел уже содержит другие уроки")
                lesson = lessons[0]
                if (lesson.title, lesson.description, lesson.order) != (LESSON["title"], LESSON["description"], 0):
                    raise ValueError("Существующий урок отличается")
                steps = (await session.scalars(select(Step).where(Step.lesson_id == lesson.id).order_by(Step.order))).all()
                expected = [(item["title"], order, item["content"]) for order, item in enumerate(LESSON["steps"])]
                if [(item.title, item.order, item.content) for item in steps] != expected:
                    raise ValueError("Существующие степы отличаются; перезапись не выполняется")
                print(f"Урок {lesson.id}: все {len(steps)} степов совпадают, изменений нет.")
                return
            section = Section(course_id=course_id, title=SECTION_TITLE, description=SECTION_DESCRIPTION, order=0)
            session.add(section)
            await session.flush()
            lesson = Lesson(section_id=section.id, title=LESSON["title"], description=LESSON["description"], order=0)
            session.add(lesson)
            await session.flush()
            session.add_all(Step(lesson_id=lesson.id, order=order, **item) for order, item in enumerate(LESSON["steps"]))
            await session.flush()
            print(f"Курс {course_id}, раздел {section.id}, урок {lesson.id}: добавлено {len(LESSON['steps'])} степов.")
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
