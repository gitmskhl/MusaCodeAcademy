"""Validate and atomically import the reviewed Python practice course.

No configured application database is used implicitly. The default is validation only.
"""
from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.models import Base, Course, Lesson, Section, Step, Task, TestCase
from app.schemas.course import CourseCreate
from app.schemas.steps.step import StepCreate
from app.schemas.task import TaskCreate
from app.schemas.testCase import TestCaseCreate

DEFAULT_BUNDLE = Path(__file__).resolve().parents[2] / "data/course_imports/python_basics_practice"
SLUG = "python-basics-practice"
COURSE_FIELDS = ("title", "slug", "short_description", "description", "level",
                 "price_label", "outcomes", "icon_url", "promo_video_url")
TASK_FIELDS = ("starter_code", "checking_mode", "time_limit_ms", "memory_limit_mb")


def all_steps(bundle: dict) -> list[dict]:
    return [step for section in bundle["sections"] for lesson in section["lessons"]
            for step in lesson["steps"]]


def task_steps(bundle: dict) -> list[dict]:
    return [step for step in all_steps(bundle) if step["task"] is not None]


def source_has_theory(source: dict) -> bool:
    return source.get("theory_required", False) or any(p["text"].strip() == "Теория" or
               "Средним числом называется" in p["text"] for p in source["paragraphs"])


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _ordered(items: list[dict]) -> bool:
    return [item["order"] for item in items] == list(range(len(items)))


def load_bundle(directory: Path = DEFAULT_BUNDLE) -> dict:
    directory = Path(directory)
    source_bytes = (directory / "sources.json").read_bytes()
    sources = json.loads(source_bytes)
    bundle = json.loads((directory / "course.json").read_text(encoding="utf-8"))
    _require(bundle.get("format_version") in {1, 2}, "Неподдерживаемый формат импорта")
    _require(bundle["source_snapshot_sha256"] == hashlib.sha256(source_bytes).hexdigest(),
             "Снимок исходников изменился: пересоберите пакет и проверьте соответствие")
    course = bundle["course"]
    _require(course["slug"] == SLUG and course["is_published"] is False,
             "Разрешён только новый черновик python-basics-practice")
    CourseCreate.model_validate(course)
    sections = bundle["sections"]
    _require(len(sections) in {4, 6} and _ordered(sections), "Нарушен состав или порядок разделов")
    source_docs = {d["id"]: d for d in sources["documents"]}
    _require(len(source_docs) == len(sources["documents"]), "Повторные исходные документы")
    lessons = [lesson for section in sections for lesson in section["lessons"]]
    _require(len(lessons) == len(source_docs) and {l["source_id"] for l in lessons} == set(source_docs),
             "Не все выбранные документы представлены уроками")
    for section in sections:
        _require(_ordered(section["lessons"]), "Нарушен порядок уроков")
        for lesson in section["lessons"]:
            source = source_docs[lesson["source_id"]]
            _require(source["section"] == section["order"] + 1,
                     "Документ попал в чужой раздел")
            _require(lesson["key"] == f"gdrive:{source['id']}" and
                     lesson["source_folder"] == source["folder_path"] and
                     lesson["source_title"] == source["title"], "Неверная ссылка на источник")
            _require(bool(lesson["steps"]) and _ordered(lesson["steps"]), "Нарушен порядок шагов")
            if bundle["format_version"] == 2:
                theory = [s for s in lesson["steps"] if s.get("kind") == "theory"]
                _require(len(theory) == int(source_has_theory(source)) and
                         (not theory or theory[0] is lesson["steps"][0]),
                         "Краткое напоминание должно быть первым шагом, если в источнике есть теория")
            _require("v0." not in lesson["title"] and "v1." not in lesson["title"] and
                     "v2." not in lesson["title"] and "v3." not in lesson["title"],
                     "Техническая версия попала в название урока")
    expected_keys = {f"gdrive:{d['id']}:task:{t['number']}" for d in source_docs.values()
                     for t in d["tasks"]}
    coverage = bundle["coverage"]
    _require(len(coverage) == len(expected_keys) and
             {c["source_key"] for c in coverage} == expected_keys,
             "Есть потерянные или повторно учтённые исходные задания")
    steps = all_steps(bundle)
    step_keys = [s["source_key"] for s in steps]
    exercises = task_steps(bundle)
    task_keys = {s["source_key"] for s in exercises}
    _require(len(step_keys) == len(set(step_keys)), "Повторный исходный ключ задачи")
    _require({c["source_key"] for c in coverage if c["status"] == "imported"} == task_keys,
             "Импортированные задания не соответствуют шагам")
    for c in coverage:
        _require(c["status"] in {"imported", "duplicate", "deferred"}, "Неизвестный статус задания")
        if c["status"] in {"imported", "duplicate"}:
            _require(c["target_key"] in task_keys, "Не найден шаг для исходного задания")
        else:
            _require(bool(c.get("reason")) and bool(c.get("proposal")), "Нет объяснения отсрочки")
    signatures = set()
    test_count = 0
    public_count = 0
    for section in sections:
        for lesson in section["lessons"]:
            for step in lesson["steps"]:
                StepCreate.model_validate(step)
                if step["task"] is None:
                    _require(step.get("kind") == "theory" and not step["tests"] and
                             step["source_key"] == f"gdrive:{lesson['source_id']}:theory",
                             "Теоретический шаг не должен содержать задачу или тесты")
                    continue
                if bundle["format_version"] == 2:
                    _require(step.get("kind") == "task", "Неизвестный вид практического шага")
                _require(step["source_key"] ==
                         f"gdrive:{lesson['source_id']}:task:{step['source_number']}",
                         "Задание привязано к другому документу")
                TaskCreate.model_validate({"step_id": 1, **step["task"]})
                starter = step["task"]["starter_code"]
                _require(starter == "# Напишите решение здесь.\n" or (
                         lesson['source_id'] == '1Tc6LhEEQueqws4AQedeQADVmUylZmCCqn2XFNwY61Ik' and
                         starter.endswith('    pass\n') and 'def check_password(' in starter),
                         "В стартовом коде не должно быть эталонного решения")
                signature = tuple(step[f].strip() for f in
                                  ("statement", "input_description", "output_description"))
                _require(signature not in signatures, "Повторяющееся условие задачи")
                signatures.add(signature)
                tests = step["tests"]
                _require(bool(tests) and _ordered(tests), "Нет тестов или нарушен их порядок")
                _require(len({t["input"] for t in tests}) == len(tests), "Повторные входы тестов")
                _require(any(not t["is_hidden"] for t in tests), "Нет открытого примера")
                for test in tests:
                    TestCaseCreate.model_validate({"task_id": 1, **test})
                    _require(test["category"] in {"example", "normal", "boundary", "unusual"},
                             "Неизвестная категория теста")
                test_count += len(tests)
                public_count += sum(not t["is_hidden"] for t in tests)
    actual = {"sections": len(sections), "lessons": len(lessons), "tasks": len(exercises),
              "tests": test_count, "public_tests": public_count,
              "hidden_tests": test_count - public_count, "source_tasks": len(coverage),
              "duplicates": sum(c["status"] == "duplicate" for c in coverage),
              "deferred": sum(c["status"] == "deferred" for c in coverage)}
    if bundle["format_version"] == 2:
        actual.update(steps=len(steps), theory_steps=len(steps) - len(exercises))
    _require(bundle["counts"] == actual, "Счётчики пакета не соответствуют содержимому")
    return bundle


def verify_reference_solutions(bundle: dict, directory: Path = DEFAULT_BUNDLE) -> int:
    """Run authored references through MCA's existing browser checker, including output limits."""
    solutions = json.loads((Path(directory) / "reference_solutions.json").read_text(encoding="utf-8"))
    steps = task_steps(bundle)
    _require(set(solutions) == {s["source_key"] for s in steps}, "Неполный набор эталонных решений")
    jobs = [(step, i, test) for step in steps for i, test in enumerate(step["tests"], 1)]
    harness = Path(__file__).resolve().parents[1] / "static/js/task-viewer/local-python-checker.py"
    runner = ("import json, runpy, sys\n"
              "check = runpy.run_path(sys.argv[1])['check_python_test']\n"
              "payload = json.load(sys.stdin)\n"
              "print(check(**payload))\n")
    with tempfile.TemporaryDirectory(prefix="mca-reference-") as working:
        def check(job: tuple[dict, int, dict]) -> None:
            step, index, test = job
            try:
                result = subprocess.run(
                    [sys.executable, "-I", "-X", "utf8", "-c", runner, str(harness)],
                    input=json.dumps({"source_code": solutions[step["source_key"]],
                                      "test_input": test["input"],
                                      "expected_output": test["expected_output"]}),
                    capture_output=True, text=True, encoding="utf-8",
                    cwd=working, timeout=step['task']['time_limit_ms'] / 1000 + 2, check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ValueError(f"{step['title']}: эталон превысил время на тесте {index}") from exc
            _require(result.returncode == 0,
                     f"{step['title']}: ошибка эталона в тесте {index}: {result.stderr[:500]}")
            checked = json.loads(result.stdout)
            _require(checked["status"] == "ACCEPTED",
                     f"{step['title']}: неверный эталон или ответ в тесте {index}: "
                     f"{checked['status']}: {checked['actual_output'][:500]}")
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(check, jobs))
    return len(jobs)


def _graph(course: Course) -> dict:
    """Only the fields controlled by this importer; IDs and timestamps stay intact."""
    return {
        "course": {f: getattr(course, f) for f in COURSE_FIELDS},
        "sections": [
            {"title": section.title, "description": section.description, "order": section.order,
             "lessons": [
                 {"title": lesson.title, "description": lesson.description, "order": lesson.order,
                  "steps": [
                      {"title": step.title, "order": step.order, "content": step.content,
                       "task": None if step.task is None else {
                           f: getattr(step.task, f) for f in TASK_FIELDS},
                       "tests": [] if step.task is None else [
                           {f: getattr(t, f) for f in
                            ("input", "expected_output", "is_hidden", "order")}
                           for t in sorted(step.task.test_cases, key=lambda t: (t.order, t.id))]}
                      for step in sorted(lesson.steps, key=lambda s: (s.order, s.id))]}
                 for lesson in sorted(section.lessons, key=lambda l: (l.order, l.id))]}
            for section in sorted(course.sections, key=lambda s: (s.order, s.id))]
    }


def _expected_graph(bundle: dict) -> dict:
    return {
        "course": {f: bundle["course"][f] for f in COURSE_FIELDS},
        "sections": [
            {**{f: s[f] for f in ("title", "description", "order")}, "lessons": [
                {**{f: l[f] for f in ("title", "description", "order")}, "steps": [
                    {**{f: step[f] for f in ("title", "order", "content", "task")}, "tests": [
                        {f: t[f] for f in ("input", "expected_output", "is_hidden", "order")}
                        for t in step["tests"]]}
                    for step in l["steps"]]} for l in s["lessons"]]}
            for s in bundle["sections"]]
    }


def _revise_course(db: AsyncSession, course: Course, previous: dict, bundle: dict) -> None:
    """Apply a reviewed revision by source keys, retaining all existing IDs and student links."""
    old_keys = [s["key"] for s in previous["sections"]]
    new_keys = [s["key"] for s in bundle["sections"]]
    _require(new_keys[:len(old_keys)] == old_keys, "Нельзя удалять или переставлять разделы")
    if (previous['source_snapshot_sha256'] != bundle['source_snapshot_sha256'] and
            len(new_keys) > len(old_keys)):
        _require(previous['sections'] == bundle['sections'][:len(old_keys)],
                 'Новый снимок может только дополнять курс разделами')
    _require({s["source_key"] for s in task_steps(previous)} <=
             {s["source_key"] for s in task_steps(bundle)},
             "Обновление не должно удалять практические задачи")
    for field in COURSE_FIELDS:
        setattr(course, field, bundle["course"][field])
    for section, old_section, new_section in zip(
        sorted(course.sections, key=lambda s: (s.order, s.id)),
        previous["sections"], bundle["sections"][:len(old_keys)], strict=True,
    ):
        old_lesson_keys = [l['key'] for l in old_section['lessons']]
        _require(old_lesson_keys == [l['key'] for l in new_section['lessons'][:len(old_lesson_keys)]],
                 "Нельзя удалять или переставлять существующие уроки")
        for field in ("title", "description", "order"):
            setattr(section, field, new_section[field])
        for lesson, old_lesson, new_lesson in zip(
            sorted(section.lessons, key=lambda l: (l.order, l.id)),
            old_section["lessons"], new_section["lessons"][:len(old_lesson_keys)], strict=True,
        ):
            for field in ("title", "description", "order"):
                setattr(lesson, field, new_lesson[field])
            existing_steps = {
                data["source_key"]: step for data, step in zip(
                    old_lesson["steps"], sorted(lesson.steps, key=lambda s: (s.order, s.id)), strict=True)}
            _require(set(existing_steps) <= {s["source_key"] for s in new_lesson["steps"]},
                     "Обновление не должно удалять существующие шаги")
            for data in new_lesson["steps"]:
                step = existing_steps.get(data["source_key"])
                if step is None:
                    _require(data["task"] is None, "Добавлять можно только теоретические шаги")
                    step = Step(lesson=lesson, task=None, **{
                        f: data[f] for f in ("title", "content", "order")})
                    db.add(step)
                else:
                    for field in ("title", "content", "order"):
                        setattr(step, field, data[field])
                if data["task"] is not None:
                    _require(step.task is not None, "У практического шага отсутствует задача")
                    for field in TASK_FIELDS:
                        setattr(step.task, field, data["task"][field])
                    _require(len(step.task.test_cases) == len(data["tests"]),
                             "Обновление не должно добавлять или удалять тесты")
                    for test, td in zip(
                        sorted(step.task.test_cases, key=lambda t: (t.order, t.id)),
                        data["tests"], strict=True,
                    ):
                        for field in ("input", "expected_output", "is_hidden", "order"):
                            setattr(test, field, td[field])

        for ld in new_section['lessons'][len(old_lesson_keys):]:
            _append_lesson(db, section, ld)

    for data in bundle["sections"][len(old_keys):]:
        section = Section(course=course, **{f: data[f] for f in ("title", "description", "order")})
        db.add(section)
        for ld in data["lessons"]:
            _append_lesson(db, section, ld)


def _append_lesson(db: AsyncSession, section: Section, data: dict) -> None:
    lesson = Lesson(section=section, **{f: data[f] for f in ('title', 'description', 'order')})
    db.add(lesson)
    for sd in data['steps']:
        step = Step(lesson=lesson, task=None, **{f: sd[f] for f in ('title', 'content', 'order')})
        db.add(step)
        if sd['task'] is not None:
            task = Task(step=step, test_cases=[], **sd['task'])
            db.add(task)
            for td in sd['tests']:
                db.add(TestCase(task=task, **{f: td[f] for f in
                           ('input', 'expected_output', 'is_hidden', 'order')}))


async def import_course(db: AsyncSession, bundle: dict, *, previous_bundle: dict | None = None) -> dict:
    """One transaction. Conflicts require an explicitly supplied, matching previous bundle."""
    _require(not db.in_transaction(), "Для импорта нужна отдельная сессия без активной транзакции")
    async with db.begin():
        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            # Serialize concurrent imports before checking whether this slug exists.
            lock_id = int.from_bytes(hashlib.sha256(SLUG.encode()).digest()[:8], "big", signed=True)
            await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        elif dialect == "sqlite":
            await db.execute(text("BEGIN IMMEDIATE"))
        existing = await db.scalar(select(Course).where(Course.slug == SLUG).options(
            selectinload(Course.sections).selectinload(Section.lessons)
            .selectinload(Lesson.steps).selectinload(Step.task).selectinload(Task.test_cases)
        ))
        if existing:
            status = "unchanged"
            if _graph(existing) != _expected_graph(bundle):
                _require(previous_bundle is not None and
                         _graph(existing) == _expected_graph(previous_bundle),
                         "Курс с этим slug уже существует и отличается. Импорт отменён без изменений.")
                _revise_course(db, existing, previous_bundle, bundle)
                await db.flush()
                _require(_graph(existing) == _expected_graph(bundle),
                         "Результат обновления не соответствует проверенному пакету")
                status = "updated"
            result = {"status": status, "course_id": existing.id,
                      "is_published": existing.is_published, "counts": bundle["counts"]}
        else:
            course = Course(**bundle["course"])
            db.add(course)
            await db.flush()
            for section_data in bundle["sections"]:
                section = Section(course_id=course.id, **{
                    f: section_data[f] for f in ("title", "description", "order")})
                db.add(section)
                await db.flush()
                for lesson_data in section_data["lessons"]:
                    lesson = Lesson(section_id=section.id, **{
                        f: lesson_data[f] for f in ("title", "description", "order")})
                    db.add(lesson)
                    await db.flush()
                    for step_data in lesson_data["steps"]:
                        step = Step(lesson_id=lesson.id, **{
                            f: step_data[f] for f in ("title", "order", "content")})
                        db.add(step)
                        await db.flush()
                        if step_data["task"] is None:
                            continue
                        task = Task(step_id=step.id, **step_data["task"])
                        db.add(task)
                        await db.flush()
                        db.add_all([TestCase(task_id=task.id, **{
                            f: t[f] for f in ("input", "expected_output", "is_hidden", "order")})
                            for t in step_data["tests"]])
            await db.flush()
            result = {"status": "created", "course_id": course.id,
                      "is_published": False, "counts": bundle["counts"]}
    # Return success only after the transaction has committed.
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    result.add_argument("--apply", action="store_true", help="Записать проверенный курс в БД")
    result.add_argument("--update-from", type=Path,
                        help="Каталог предыдущего пакета для обновления совпадающего с ним курса")
    result.add_argument("--database-url-env", default="MCA_IMPORT_DATABASE_URL",
                        help="Переменная окружения с URL целевой БД; .env приложения не используется")
    result.add_argument("--environment", choices=("development", "test", "production"))
    result.add_argument("--confirm-production-import", action="store_true",
                        help="Только после отдельного явного согласования production-импорта")
    result.add_argument("--preview-db", type=Path,
                        help="Создать схему текущих моделей только в новой отдельной SQLite-БД")
    result.add_argument("--result-file", type=Path, help="Сохранить результат, ID и счётчики в JSON")
    return result


async def run(args: argparse.Namespace) -> dict:
    bundle = load_bundle(args.bundle)
    previous = load_bundle(args.update_from) if args.update_from else None
    verified = await asyncio.to_thread(verify_reference_solutions, bundle, args.bundle)
    if not args.apply:
        return {"status": "validated", "reference_tests_passed": verified, "counts": bundle["counts"]}
    _require(args.environment is not None, "Для --apply явно укажите --environment")
    if args.environment == "production":
        _require(args.confirm_production_import,
                 "Production требует отдельного подтверждения и --confirm-production-import")
    if args.preview_db:
        _require(args.environment in {"development", "test"},
                 "Preview разрешён только для development/test")
        preview = args.preview_db.resolve()
        _require(not preview.exists(), "Preview-БД уже существует; для повтора передайте её URL через переменную окружения")
        preview.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite+aiosqlite:///{preview}"
    else:
        database_url = os.environ.get(args.database_url_env, "")
        _require(bool(database_url), f"Задайте URL целевой БД в {args.database_url_env}")
    engine = create_async_engine(database_url)
    try:
        if args.preview_db:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            result = await import_course(session, bundle, previous_bundle=previous)
        result["reference_tests_passed"] = verified
        result["environment"] = args.environment
        return result
    finally:
        await engine.dispose()


def main() -> None:
    args = parser().parse_args()
    try:
        result = asyncio.run(run(args))
        output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.result_file:
            args.result_file.parent.mkdir(parents=True, exist_ok=True)
            args.result_file.write_text(output, encoding="utf-8")
        print(output, end="")
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit(f"Импорт отменён: {exc}") from None
    except Exception as exc:
        # Database errors can include credentials/parameters: do not print connection strings.
        raise SystemExit(f"Импорт не выполнен ({type(exc).__name__}); транзакция отменена.") from None


if __name__ == "__main__":
    main()
