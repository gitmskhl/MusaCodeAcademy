import ast
from copy import deepcopy

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.cli import import_python_practice as importer
from app.cli.update_python_practice_dictionaries import apply_update, slice_spec
from app.models import Base, Course, Enrollment, Section, Step, StepProgress, Submission, User
from app.enums import SubmissionStatus
from scripts.python_practice_dictionaries import build, validate


async def snapshot(db):
    result = {table.name: {(row["id"] if "id" in table.c else tuple(row[c.name] for c in table.primary_key)): dict(row) for row in
                          (await db.execute(select(table))).mappings()}
              for table in Base.metadata.sorted_tables}
    await db.rollback()
    return result


async def legacy_course(db, bundle):
    previous = deepcopy(bundle)
    spec = slice_spec(previous)
    # Recreate the former output, preserving invitations and input data.
    spec["content"]["blocks"][0]["data"]["text"] = "Выведи первые элементы, каждый с новой строки."
    for test in spec["tests"]:
        prefix, values = test["expected_output"].rsplit("\n", 2)[:2]
        test["expected_output"] = prefix + "\n" + "".join(f"{n}\n" for n in ast.literal_eval(values))
    result = await importer.import_course(db, previous)
    course = await db.get(Course, result["course_id"])
    course.is_published = True
    db.add(Section(course=course, title="Дополнительный раздел", description="Сохранить", order=6))
    step = await db.scalar(select(Step).where(Step.title == "Первые элементы списка").options(selectinload(Step.task)))
    user = User(email="dictionaries@example.test", password_hash="unused", first_name="Student", last_name="Test")
    db.add(user)
    await db.flush()
    db.add_all([Enrollment(user_id=user.id, course_id=course.id),
                StepProgress(user_id=user.id, step_id=step.id),
                Submission(task_id=step.task.id, user_id=user.id, source_code="print(1)",
                           status=SubmissionStatus.ACCEPTED, passed_tests=6, total_tests=6)])
    await db.commit()
    return previous, step.id


def test_dictionary_materials_and_reference_answers():
    section, solutions, examples = build()
    assert validate(section, solutions, examples) == dict(lessons=6, theory_steps=6, tasks=18, tests=64)
    for lesson in section["lessons"]:
        assert [s["kind"] for s in lesson["steps"]] == ["theory", "task", "task", "task"]
        assert [s["order"] for s in lesson["steps"]] == [0, 1, 2, 3]
        for step in lesson["steps"][1:]:
            assert any(test["is_hidden"] for test in step["tests"])
            assert step["task"]["starter_code"] == "# Напишите решение здесь.\n"


@pytest.mark.asyncio
async def test_update_preserves_existing_data_and_is_idempotent(db):
    bundle = importer.load_bundle()
    previous, step_id = await legacy_course(db, bundle)
    before = await snapshot(db)
    section, _, _ = build()
    first = await apply_update(db, bundle, section, previous=previous)
    assert first["status"] == "updated" and first["is_published"] is True
    assert first["slice_step_id"] == step_id
    after = await snapshot(db)
    task_id = next(t for t, row in before["tasks"].items() if row["step_id"] == step_id)
    changed_tests = {row_id for row_id, row in before["test_cases"].items() if row["task_id"] == task_id}
    for table, rows in before.items():
        for row_id, row in rows.items():
            if (table == "steps" and row_id == step_id) or (table == "test_cases" and row_id in changed_tests):
                fields = {"updated_at", "content" if table == "steps" else "expected_output"}
                assert {k: v for k, v in after[table][row_id].items() if k not in fields} == {
                    k: v for k, v in row.items() if k not in fields}
            else:
                assert after[table][row_id] == row
    for table, count in dict(sections=1, lessons=6, steps=24, tasks=18, test_cases=64).items():
        assert len(after[table]) - len(before[table]) == count
    assert after["sections"][first["dictionaries_section_id"]]["order"] == 7
    again = await apply_update(db, bundle, section)
    assert again["status"] == "unchanged"
    assert await snapshot(db) == after


@pytest.mark.asyncio
async def test_conflicting_section_rolls_back_slice_changes(db):
    bundle = importer.load_bundle()
    previous, _ = await legacy_course(db, bundle)
    course_id = await db.scalar(select(Course.id).where(Course.slug == importer.SLUG))
    db.add(Section(course_id=course_id, title="Словари", description="Другие материалы", order=7))
    await db.commit()
    before = await snapshot(db)
    with pytest.raises(ValueError, match="отличается"):
        await apply_update(db, bundle, build()[0], previous=previous)
    assert await snapshot(db) == before


@pytest.mark.asyncio
async def test_slice_revision_requires_matching_baseline(db):
    bundle = importer.load_bundle()
    await legacy_course(db, bundle)
    before = await snapshot(db)
    with pytest.raises(ValueError, match="предыдущего пакета"):
        await apply_update(db, bundle, build()[0])
    assert await snapshot(db) == before
