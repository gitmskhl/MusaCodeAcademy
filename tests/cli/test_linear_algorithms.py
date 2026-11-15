"""Проверяем проверяющую программу и безопасное добавление раздела."""
from copy import deepcopy
import json
from pathlib import Path
import runpy

import pytest
from sqlalchemy import select

from app.models import Base, Course, Lesson, Section, Step
from data.linear_algorithms import build
from data.linear_algorithms.content import LESSONS


async def snapshot(db):
    result = {}
    for table in Base.metadata.sorted_tables:
        rows = (await db.execute(select(table))).mappings().all()
        result[table.name] = {row['id']: dict(row) for row in rows}
    await db.rollback()
    return result


async def seed(db, slug=build.SLUG):
    course = Course(title='Основы Python. Практика.', slug=slug,
        short_description='Практика', description='Описание', is_published=True,
        sections=[Section(title='Прежний раздел', order=8, lessons=[Lesson(title='Прежний урок', order=0,
            steps=[Step(title='Прежний шаг', order=0, content={'version': 1, 'layout': 'vertical', 'blocks': []})])])])
    db.add(course)
    await db.commit()
    return course.id


def test_all_answers_pass_the_actual_student_checker():
    check = runpy.run_path(str(Path('app/static/js/task-viewer/local-python-checker.py')))['check_python_test']
    for lesson in LESSONS:
        for source in lesson['steps']:
            if source['kind'] == 'theory':
                for example in source['examples']:
                    assert json.loads(check(example['code'], '', example['output']))['status'] == 'ACCEPTED'
                continue
            for case in source['tests']:
                assert json.loads(check(source['reference'], case['input'], case['expected_output']))['status'] == 'ACCEPTED', source['title']


def test_exports_match_validated_content_and_keep_solutions_private():
    data = build.validate()
    assert json.loads((build.ROOT/'section.json').read_text()) == data
    for group, lesson in zip(LESSONS, data['lessons'], strict=True):
        assert lesson['steps'][0]['task'] is None
        for source, step in zip(group['steps'][1:], lesson['steps'][1:], strict=True):
            assert step['task']['starter_code'] == '# Напиши программу здесь\n'
            assert source['reference'] not in json.dumps(step, ensure_ascii=False)
            assert sum(not t['is_hidden'] for t in step['tests']) == 2
            assert not any(b['type'] == 'code' for b in step['content']['blocks'])


@pytest.mark.asyncio
async def test_import_preserves_all_existing_rows_and_repeats_without_changes(db):
    course_id = await seed(db)
    before = await snapshot(db)
    data = build.payload()
    result = await build.import_section(db, data, course_id)
    assert result['status'] == 'created'
    assert result['is_published'] is True
    after = await snapshot(db)
    for table, rows in before.items():
        for row_id, row in rows.items():
            assert after[table][row_id] == row
    for table, count in {'sections': 1, 'lessons': 5, 'steps': 25, 'tasks': 20, 'test_cases': 129}.items():
        assert len(after[table]) - len(before[table]) == count
    assert after['sections'][result['section_id']]['order'] == 9
    assert (await build.import_section(db, data, course_id))['status'] == 'unchanged'
    assert await snapshot(db) == after


@pytest.mark.asyncio
async def test_changed_content_is_rejected_atomically(db):
    course_id = await seed(db)
    data = build.payload()
    await build.import_section(db, data, course_id)
    before = await snapshot(db)
    changed = deepcopy(data)
    changed['lessons'][0]['steps'][1]['content']['blocks'][0]['data']['text'] = 'Другое условие'
    with pytest.raises(ValueError, match='Раздел отличается'):
        await build.import_section(db, changed, course_id)
    assert await snapshot(db) == before


@pytest.mark.asyncio
async def test_wrong_course_is_rejected_without_writes(db):
    course_id = await seed(db, 'another-course')
    before = await snapshot(db)
    with pytest.raises(ValueError, match='python-basics-practice'):
        await build.import_section(db, build.payload(), course_id)
    assert await snapshot(db) == before
