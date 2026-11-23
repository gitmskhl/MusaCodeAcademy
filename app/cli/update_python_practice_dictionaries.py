"""Validate or atomically add the dictionary supplement and revise the slice task.

Only the target step and the new section are owned by this update. Other course
materials, metadata, publication, existing IDs and student records stay intact.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.cli import import_python_practice as importer
from app.models import Course, Lesson, Section, Step, Task


SLICE_KEY = "gdrive:1D1dnmiXSkyOZHjoa3VjaK_09dhHsYa7GssLnGgWgNz0:task:1"


def slice_spec(bundle):
    return next(s for s in importer.task_steps(bundle) if s["source_key"] == SLICE_KEY)


def step_graph(spec):
    return {**{f: spec[f] for f in ("title", "order", "content", "task")},
            "tests": [{f: test[f] for f in ("input", "expected_output", "is_hidden", "order")}
                      for test in spec["tests"]]}


async def apply_update(db, bundle, supplement, *, previous=None):
    importer._require(not db.in_transaction(), "Для обновления нужна отдельная сессия")
    async with db.begin():
        if db.get_bind().dialect.name == "postgresql":
            key = int.from_bytes(hashlib.sha256(importer.SLUG.encode()).digest()[:8], "big", signed=True)
            await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
        elif db.get_bind().dialect.name == "sqlite":
            await db.execute(text("BEGIN IMMEDIATE"))
        course = await db.scalar(select(Course).where(Course.slug == importer.SLUG).with_for_update().options(
            selectinload(Course.sections).selectinload(Section.lessons).selectinload(Lesson.steps)
            .selectinload(Step.task).selectinload(Task.test_cases)))
        importer._require(course is not None, "Курс «Основы Python. Практика.» не найден")
        sections = sorted(course.sections, key=lambda s: (s.order, s.id))
        candidates = [step for section in sections if section.title == "Списки"
                      for lesson in section.lessons if lesson.title == "Срезы: начало, хвост и разворот"
                      for step in lesson.steps if step.title == "Первые элементы списка"]
        importer._require(len(candidates) == 1, "Не найден единственный целевой шаг со срезами")
        step = candidates[0]
        current = next(s for section in importer._graph(course)["sections"]
                       if section["title"] == "Списки"
                       for lesson in section["lessons"] for s in lesson["steps"]
                       if s["title"] == step.title and s["order"] == step.order
                       and lesson["title"] == "Срезы: начало, хвост и разворот")
        expected = step_graph(slice_spec(bundle))
        changed = current != expected
        if changed:
            importer._require(previous is not None and current == step_graph(slice_spec(previous)),
                              "Шаг со срезами отличается от предыдущего пакета; обновление отменено")
            importer._require(current["task"] == expected["task"] and
                              len(current["tests"]) == len(expected["tests"]),
                              "Обновление срезов не должно менять задачу или количество тестов")
            step.content = expected["content"]
            for saved, old, new in zip(sorted(step.task.test_cases, key=lambda t: (t.order, t.id)),
                                       current["tests"], expected["tests"], strict=True):
                importer._require(all(old[f] == new[f] for f in ("input", "is_hidden", "order")),
                                  "Обновление срезов должно менять только ожидаемые ответы тестов")
                saved.expected_output = new["expected_output"]
        dictionaries = [s for s in sections if s.title == supplement["title"]]
        importer._require(len(dictionaries) <= 1, "Найдено несколько разделов «Словари»")
        if dictionaries:
            section = dictionaries[0]
            source = deepcopy(supplement)
            source["order"] = section.order
            expected_section = importer._expected_graph(dict(course=bundle["course"], sections=[source]))["sections"][0]
            actual_section = next(s for s in importer._graph(course)["sections"] if s["title"] == source["title"])
            importer._require(actual_section == expected_section,
                              "Существующий раздел «Словари» отличается; обновление отменено")
        else:
            section = Section(course=course, title=supplement["title"], description=supplement["description"],
                              order=max((s.order for s in sections), default=-1) + 1)
            db.add(section)
            for lesson in supplement["lessons"]:
                importer._append_lesson(db, section, lesson)
        await db.flush()
        result = dict(status="updated" if changed or not dictionaries else "unchanged",
                      course_id=course.id, is_published=course.is_published,
                      slice_step_id=step.id, dictionaries_section_id=section.id,
                      lessons=[dict(id=lesson.id, title=lesson.title) for lesson in section.lessons])
    return result


async def run(args):
    from scripts.python_practice_dictionaries import build, validate
    bundle = importer.load_bundle()
    supplement, solutions, examples = build()
    exported = json.loads((importer.DEFAULT_BUNDLE / "dictionaries.json").read_text(encoding="utf-8"))
    importer._require(exported == supplement, "Пересобери пакет словарей")
    exported_solutions = json.loads((importer.DEFAULT_BUNDLE / "dictionaries_reference_solutions.json").read_text(encoding="utf-8"))
    importer._require(exported_solutions == solutions, "Пересобери эталонные решения словарей")
    counts = validate(supplement, solutions, examples)
    checked = await asyncio.to_thread(importer.verify_reference_solutions, bundle)
    result = dict(status="validated", dictionaries=counts, base_reference_tests_passed=checked)
    if args.apply:
        url = os.environ.get(args.database_url_env)
        importer._require(bool(url), f"Задай URL целевой базы в {args.database_url_env}")
        previous = importer.load_bundle(args.update_from) if args.update_from else None
        engine = create_async_engine(url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as db:
                result.update(await apply_update(db, bundle, supplement, previous=previous))
        finally:
            await engine.dispose()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--update-from", type=Path, help="Предыдущий пакет для сверки шага со срезами")
    parser.add_argument("--database-url-env", default="MCA_IMPORT_DATABASE_URL")
    parser.add_argument("--result-file", type=Path)
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args))
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit(f"Обновление отменено: {exc}") from None
    except Exception as exc:
        # Connection errors may contain credentials; avoid printing them.
        raise SystemExit(f"Обновление отменено ({type(exc).__name__}). Транзакция не применена.") from None
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.result_file:
        args.result_file.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
