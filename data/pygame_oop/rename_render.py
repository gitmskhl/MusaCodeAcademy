"""Обновление названия draw → render с сохранением ID шагов и прогресса."""
import asyncio
import json

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine
from app.models import Course, Section, Lesson, Step
from .build import ROOT, SLUG, snapshot, verify_section, write_json
from .content import illustrated_sections


async def main():
    desired = illustrated_sections()
    baseline = json.loads((ROOT / 'revisions/before-render-sections.json').read_text())
    changed = 0
    try:
        async with AsyncSessionLocal() as session, session.begin():
            course = await session.scalar(select(Course).where(Course.id == 3).with_for_update())
            assert course is not None and course.slug == SLUG
            targets = (await session.scalars(select(Section).where(
                Section.course_id == course.id, Section.order.in_([2, 3])).order_by(Section.order))).all()
            assert len(targets) == 2
            untouched = await snapshot(session, course.id, [s.id for s in targets])
            path = ROOT / 'revisions/before-render-update.json'
            if not path.exists():
                write_json('revisions/before-render-update.json', await snapshot(session, course.id))
            for order, (target, old, new) in enumerate(zip(targets, baseline, desired, strict=True), 2):
                try:
                    await verify_section(session, target, new, order)
                    continue
                except ValueError:
                    await verify_section(session, target, old, order)
                lessons = (await session.scalars(select(Lesson).where(Lesson.section_id == target.id).order_by(Lesson.order))).all()
                for lesson, source in zip(lessons, new['lessons'], strict=True):
                    rows = (await session.scalars(select(Step).where(Step.lesson_id == lesson.id).order_by(Step.order))).all()
                    for row, item in zip(rows, source['steps'], strict=True):
                        if (row.title, row.content) != (item['title'], item['content']):
                            row.title, row.content = item['title'], item['content']
                            changed += 1
                await session.flush()
                await verify_section(session, target, new, order)
            assert await snapshot(session, course.id, [s.id for s in targets]) == untouched
        print(f'Обновлены {changed} шагов; ID, порядок, GIF и остальные разделы сохранены.')
    finally:
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
