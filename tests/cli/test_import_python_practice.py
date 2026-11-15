import asyncio
from copy import deepcopy
import json

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.cli import import_python_practice as importer
from app.enums import SubmissionStatus
from app.models import (
    Base, Course, Enrollment, Lesson, Section, Step, StepProgress, Submission,
    Task, TestCase as DbTestCase, User,
)


@pytest.fixture
def bundle():
    return importer.load_bundle()


async def snapshot(db):
    result = {}
    for table in Base.metadata.sorted_tables:
        rows = (await db.execute(select(table))).mappings().all()
        result[table.name] = {row["id"]: dict(row) for row in rows}
    await db.rollback()
    return result


async def seed_existing_data(db):
    task = Task(starter_code="print(1)", test_cases=[
        DbTestCase(input="", expected_output="1", order=0)])
    step = Step(title="Существующий шаг", order=0, content={
        "version": 1, "layout": "vertical", "blocks": []}, task=task)
    course = Course(
        title="Python. Основы", slug="python-basics",
        short_description="Существующее описание", description="Материалы прежнего курса",
        is_published=True, sections=[
            Section(title="Прежний раздел", order=0, lessons=[
                Lesson(title="Прежний урок", order=0, steps=[step])])])
    user = User(email="preserve@example.com", password_hash="unused",
                first_name="Old", last_name="Student")
    db.add_all([course, user])
    await db.flush()
    db.add_all([
        Enrollment(user_id=user.id, course_id=course.id),
        StepProgress(user_id=user.id, step_id=step.id),
        Submission(task_id=task.id, user_id=user.id, source_code="print(1)",
                   status=SubmissionStatus.ACCEPTED, passed_tests=1, total_tests=1),
    ])
    await db.commit()


def assert_existing_unchanged(before, after):
    for table, rows in before.items():
        for row_id, row in rows.items():
            assert after[table][row_id] == row


def test_source_coverage_and_all_reference_answers(bundle):
    assert bundle["counts"] == {
        "sections": 6, "lessons": 40, "tasks": 104, "tests": 510,
        "steps": 128, "theory_steps": 24,
        "public_tests": 107, "hidden_tests": 403, "source_tasks": 110,
        "duplicates": 4, "deferred": 2,
    }
    assert importer.verify_reference_solutions(bundle) == 510


def test_wrong_reference_is_detected(bundle, tmp_path):
    solutions = json.loads((importer.DEFAULT_BUNDLE / "reference_solutions.json").read_text())
    step = importer.task_steps(bundle)[0]
    solutions[step["source_key"]] = "print(0)\n"
    (tmp_path / "reference_solutions.json").write_text(json.dumps(solutions))
    with pytest.raises(ValueError, match="неверный эталон"):
        importer.verify_reference_solutions(bundle, tmp_path)


@pytest.mark.parametrize("corruption", ["missing_task", "changed_source", "duplicate_key"])
def test_corrupt_bundle_fails_before_database_access(bundle, tmp_path, corruption):
    sources = (importer.DEFAULT_BUNDLE / "sources.json").read_bytes()
    if corruption == "missing_task":
        bundle["sections"][0]["lessons"][0]["steps"].pop()
    elif corruption == "changed_source":
        sources += b"\n"
    else:
        first = bundle["sections"][0]["lessons"][0]["steps"][0]
        bundle["sections"][0]["lessons"][0]["steps"].append(deepcopy(first))
    (tmp_path / "sources.json").write_bytes(sources)
    (tmp_path / "course.json").write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(ValueError):
        importer.load_bundle(tmp_path)


@pytest.mark.asyncio
async def test_import_is_idempotent_and_preserves_old_course_and_student_data(db, bundle):
    await seed_existing_data(db)
    before = await snapshot(db)
    first = await importer.import_course(db, bundle)
    assert first["status"] == "created"
    assert first["is_published"] is False
    after = await snapshot(db)
    assert_existing_unchanged(before, after)
    for table, amount in {"courses": 1, "sections": 6, "lessons": 40,
                          "steps": 128, "tasks": 104, "test_cases": 510}.items():
        assert len(after[table]) - len(before[table]) == amount
    second = await importer.import_course(db, bundle)
    assert second["status"] == "unchanged"
    assert second["course_id"] == first["course_id"]
    assert await snapshot(db) == after


@pytest.mark.asyncio
async def test_repeat_does_not_unpublish_a_manually_published_course(db, bundle):
    result = await importer.import_course(db, bundle)
    course = await db.get(Course, result["course_id"])
    course.is_published = True
    await db.commit()
    before = await snapshot(db)
    repeated = await importer.import_course(db, bundle)
    assert repeated["status"] == "unchanged"
    assert repeated["is_published"] is True
    assert await snapshot(db) == before


@pytest.mark.asyncio
async def test_existing_conflicting_slug_is_not_overwritten(db, bundle):
    db.add(Course(title="Чужой курс", slug=importer.SLUG,
                  short_description="Сохранить", description="Сохранить"))
    await db.commit()
    before = await snapshot(db)
    with pytest.raises(ValueError, match="отличается"):
        await importer.import_course(db, bundle)
    assert await snapshot(db) == before


@pytest.mark.asyncio
async def test_edited_step_is_not_overwritten_on_repeat(db, bundle):
    await importer.import_course(db, bundle)
    step = await db.scalar(select(Step).order_by(Step.id).limit(1))
    step.title = "Ручная правка администратора"
    await db.commit()
    before = await snapshot(db)
    with pytest.raises(ValueError, match="отличается"):
        await importer.import_course(db, bundle)
    assert await snapshot(db) == before


@pytest.mark.asyncio
async def test_partial_import_rolls_back_without_touching_existing_data(db, bundle, monkeypatch):
    await seed_existing_data(db)
    before = await snapshot(db)
    original_flush = db.flush
    calls = 0

    async def fail_during_import(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 14:
            raise RuntimeError("injected failure")
        return await original_flush(*args, **kwargs)

    monkeypatch.setattr(db, "flush", fail_during_import)
    with pytest.raises(RuntimeError, match="injected failure"):
        await importer.import_course(db, bundle)
    assert await snapshot(db) == before


@pytest.mark.asyncio
async def test_concurrent_imports_create_one_course(db, bundle):
    sessions = async_sessionmaker(db.bind, expire_on_commit=False)
    async with sessions() as first, sessions() as second:
        results = await asyncio.gather(
            importer.import_course(first, bundle), importer.import_course(second, bundle))
    assert {r["status"] for r in results} == {"created", "unchanged"}
    assert len({r["course_id"] for r in results}) == 1
    assert await db.scalar(select(func.count()).select_from(Course)) == 1


@pytest.mark.asyncio
async def test_draft_is_visible_to_admin_and_absent_from_public_catalog(
    client, admin_headers, db, bundle,
):
    await db.rollback()
    result = await importer.import_course(db, bundle)
    response = await client.get("/api/courses", headers=admin_headers)
    assert response.status_code == 200
    assert all(c["slug"] != importer.SLUG for c in response.json())
    steps = (await db.scalars(select(Step).order_by(Step.id))).all()
    assert len(steps) == 128
    practical = [s for s in steps if s.title in
                 {importer.task_steps(bundle)[0]["title"], importer.task_steps(bundle)[-1]["title"]}]
    assert len(practical) == 2
    for step in practical:
        response = await client.get(f"/api/steps/{step.id}/admin", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        text = data["content"]["blocks"][0]["data"]["text"]
        assert "### Входные данные" not in text and "### Выходные данные" not in text
        assert "**Ввод**" not in text and "**Вывод**" not in text
        blocks = data["content"]["blocks"]
        assert any(b["type"] == "text" and b["data"]["text"] == "### Пример работы 1"
                   for b in blocks)
        assert any(b["type"] == "console" and b["data"]["lines"] for b in blocks)
        task = await db.scalar(select(Task).where(Task.step_id == step.id))
        assert "return candidate" not in task.starter_code
        assert "reference_solution" not in json.dumps(data)
    theory = steps[0]
    assert "Краткое напоминание" in theory.title and theory.order == 0
    assert await db.scalar(select(Task).where(Task.step_id == theory.id)) is None
    course = await db.get(Course, result["course_id"])
    assert course.is_published is False


@pytest.mark.asyncio
@pytest.mark.parametrize("production", [False, True])
async def test_validation_and_unconfirmed_production_never_open_database(monkeypatch, production):
    def no_database(*args, **kwargs):
        pytest.fail("Database must not be opened")

    monkeypatch.setattr(importer, "create_async_engine", no_database)
    monkeypatch.setattr(importer, "verify_reference_solutions", lambda *args: 377)
    args = importer.parser().parse_args(
        ["--apply", "--environment", "production"] if production else [])
    if production:
        with pytest.raises(ValueError, match="отдельного подтверждения"):
            await importer.run(args)
    else:
        result = await importer.run(args)
        assert result["status"] == "validated"


def without_reminders(bundle):
    previous = deepcopy(bundle)
    previous["format_version"] = 1
    previous["counts"].pop("steps")
    previous["counts"].pop("theory_steps")
    for section in previous["sections"]:
        for lesson in section["lessons"]:
            lesson["steps"] = [s for s in lesson["steps"] if s["task"] is not None]
            for order, step in enumerate(lesson["steps"]):
                step.pop("kind")
                step["order"] = order
    first = importer.task_steps(previous)[0]
    first["content"]["blocks"][0]["data"]["text"] = "Предыдущее условие"
    first["tests"][0]["expected_output"] = "Предыдущий ответ\n"
    return previous


@pytest.mark.asyncio
async def test_reviewed_update_preserves_publication_ids_progress_and_submissions(db, bundle):
    await seed_existing_data(db)
    previous = without_reminders(bundle)
    original = await importer.import_course(db, previous)
    course = await db.get(Course, original["course_id"])
    course.is_published = True
    step = await db.scalar(select(Step).join(Lesson).join(Section).where(
        Section.course_id == course.id).order_by(Step.id).limit(1))
    task = await db.scalar(select(Task).where(Task.step_id == step.id))
    original_step_id = step.id
    student = await db.scalar(select(User).where(User.email == "preserve@example.com"))
    db.add_all([
        Enrollment(user_id=student.id, course_id=course.id),
        StepProgress(user_id=student.id, step_id=step.id),
        Submission(task_id=task.id, user_id=student.id, source_code="print(14756)",
                   status=SubmissionStatus.ACCEPTED, passed_tests=1, total_tests=1),
    ])
    await db.commit()
    before = await snapshot(db)
    updated = await importer.import_course(db, bundle, previous_bundle=previous)
    assert updated["status"] == "updated"
    assert updated["course_id"] == original["course_id"] and updated["is_published"] is True
    after = await snapshot(db)
    for name in before:
        assert set(before[name]) <= set(after[name]), name
        if name not in {"steps", "lessons", "test_cases"}:
            assert after[name] == before[name], name
    assert len(after["steps"]) - len(before["steps"]) == 24
    assert len(after["tasks"]) == len(before["tasks"])
    assert set(after["test_cases"]) == set(before["test_cases"])
    assert after["steps"][original_step_id]["order"] == 1
    assert after["steps"][original_step_id]["content"] == importer.task_steps(bundle)[0]["content"]
    repeated = await importer.import_course(db, bundle, previous_bundle=previous)
    assert repeated["status"] == "unchanged" and repeated["is_published"] is True
    assert await snapshot(db) == after


@pytest.mark.asyncio
async def test_reviewed_update_refuses_a_stale_baseline(db, bundle):
    previous = without_reminders(bundle)
    await importer.import_course(db, previous)
    step = await db.scalar(select(Step).order_by(Step.id).limit(1))
    step.title = "Более свежая ручная правка"
    await db.commit()
    before = await snapshot(db)
    with pytest.raises(ValueError, match="отличается"):
        await importer.import_course(db, bundle, previous_bundle=previous)
    assert await snapshot(db) == before


@pytest.mark.asyncio
async def test_reviewed_update_rolls_back_after_flushing_changes(db, bundle, monkeypatch):
    previous = without_reminders(bundle)
    await importer.import_course(db, previous)
    before = await snapshot(db)
    original_flush = db.flush

    async def failing_flush(*args, **kwargs):
        await original_flush(*args, **kwargs)
        raise RuntimeError("revision failure")

    monkeypatch.setattr(db, "flush", failing_flush)
    with pytest.raises(RuntimeError, match="revision failure"):
        await importer.import_course(db, bundle, previous_bundle=previous)
    assert await snapshot(db) == before


def test_input_prompts_are_checked_even_when_there_are_no_result_lines(bundle):
    exercises = {s["title"]: s for s in importer.task_steps(bundle)}
    repeat = exercises["Несколько приветствий"]
    assert next(t for t in repeat["tests"] if t["input"] == "0\n")["expected_output"] == \
        "Введите количество:\n"
    age = exercises["Ожидание возраста больше восемнадцати"]
    assert age["tests"][0]["expected_output"] == (
        "Введите ваш возраст:\n" * 3 + "Вы совершеннолетний\n")
    filtered = exercises["Положительные числа из списка"]
    assert next(t for t in filtered["tests"] if t["input"] == "0\n" * 5)["expected_output"] == (
        "Введите 5 чисел\nПоложительные числа:\n")


def test_every_source_with_theory_has_a_separate_first_step(bundle):
    sources = json.loads((importer.DEFAULT_BUNDLE / "sources.json").read_text())
    by_id = {d["id"]: d for d in sources["documents"]}
    for section in bundle["sections"]:
        for lesson in section["lessons"]:
            theory = [s for s in lesson["steps"] if s["task"] is None]
            assert len(theory) == int(importer.source_has_theory(by_id[lesson["source_id"]]))
            if theory:
                assert theory[0] is lesson["steps"][0] and theory[0]["tests"] == []


@pytest.mark.parametrize(("title", "transcript"), [
    ("Произведение трёх чисел", "14756\n"),
    ("Приветствие по имени и фамилии",
     "Введите ваше имя:\nСаша\nВведите вашу фамилию:\nИванов\nЗдравствуйте, Саша Иванов\n"),
    ("Ожидание возраста больше восемнадцати",
     "Введите ваш возраст:\n15\nВведите ваш возраст:\n17\nВведите ваш возраст:\n20\nВы совершеннолетний\n"),
    ("Четыре проверки наличия", "Введите 4 числа:\n7\nда\n15\nнет\n23\nда\n8\nнет\n"),
])
def test_examples_show_the_actual_order_of_prompts_input_and_answers(bundle, title, transcript):
    step = next(s for s in importer.task_steps(bundle) if s["title"] == title)
    example = step["tests"][0]
    assert example["transcript"] == transcript
    console = next(b for b in step["content"]["blocks"] if b["type"] == "console")
    console_lines = console["data"]["lines"]
    assert "\n".join(line["text"] for line in console_lines) + "\n" == transcript
    assert [line["text"] for line in console_lines if line["type"] == "input"] == \
        example["input"].splitlines()
    assert "\n".join(line["text"] for line in console_lines
                     if line["type"] == "output").splitlines() == \
        example["expected_output"].splitlines()
    if example["input"]:
        assert example["expected_output"] != transcript


def original_four_sections(bundle):
    previous = deepcopy(bundle)
    previous['sections'] = previous['sections'][:4]
    previous['source_snapshot_sha256'] = 'previous-reviewed-source-snapshot'
    return previous


@pytest.mark.asyncio
async def test_append_sections_preserves_every_existing_row(db, bundle):
    await seed_existing_data(db)
    previous = original_four_sections(bundle)
    first = await importer.import_course(db, previous)
    course = await db.get(Course, first['course_id'])
    course.is_published = True
    await db.commit()
    before = await snapshot(db)
    result = await importer.import_course(db, bundle, previous_bundle=previous)
    assert result['status'] == 'updated' and result['is_published'] is True
    after = await snapshot(db)
    assert_existing_unchanged(before, after)
    for table, count in {'sections': 2, 'lessons': 11, 'steps': 39,
                         'tasks': 28, 'test_cases': 133}.items():
        assert len(after[table]) - len(before[table]) == count
    assert (await importer.import_course(db, bundle))['status'] == 'unchanged'
    assert await snapshot(db) == after


@pytest.mark.asyncio
async def test_append_sections_rejects_changes_to_previous_materials(db, bundle):
    previous = original_four_sections(bundle)
    await importer.import_course(db, previous)
    before = await snapshot(db)
    changed = deepcopy(bundle)
    changed['sections'][0]['lessons'][0]['title'] = 'Unexpected change'
    with pytest.raises(ValueError, match='только дополнять'):
        await importer.import_course(db, changed, previous_bundle=previous)
    assert await snapshot(db) == before


@pytest.mark.asyncio
async def test_append_sections_rolls_back_all_added_content(db, bundle, monkeypatch):
    previous = original_four_sections(bundle)
    await importer.import_course(db, previous)
    before = await snapshot(db)
    flush = db.flush

    async def fail_after_flush(*args, **kwargs):
        await flush(*args, **kwargs)
        raise RuntimeError('append failure')

    monkeypatch.setattr(db, 'flush', fail_after_flush)
    with pytest.raises(RuntimeError, match='append failure'):
        await importer.import_course(db, bundle, previous_bundle=previous)
    assert await snapshot(db) == before


@pytest.mark.asyncio
async def test_append_lesson_within_functions_preserves_rows_and_rolls_back(db, bundle, monkeypatch):
    previous = deepcopy(bundle)
    previous['sections'][-1]['lessons'].pop()
    previous['source_snapshot_sha256'] = 'previous-reviewed-snapshot'
    await importer.import_course(db, previous)
    before = await snapshot(db)
    flush = db.flush

    async def fail(*args, **kwargs):
        await flush(*args, **kwargs)
        raise RuntimeError('injected lesson failure')

    monkeypatch.setattr(db, 'flush', fail)
    with pytest.raises(RuntimeError, match='injected lesson failure'):
        await importer.import_course(db, bundle, previous_bundle=previous)
    assert await snapshot(db) == before
    monkeypatch.setattr(db, 'flush', flush)
    result = await importer.import_course(db, bundle, previous_bundle=previous)
    assert result['status'] == 'updated'
    after = await snapshot(db)
    assert_existing_unchanged(before, after)
    assert {name: len(after[name]) - len(before[name]) for name in before
            if len(after[name]) != len(before[name])} == {
                'lessons': 1, 'steps': 2, 'tasks': 1, 'test_cases': 5}
    assert (await importer.import_course(db, bundle))['status'] == 'unchanged'
