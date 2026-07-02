from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models import Lesson
from app.schemas.lesson import (
    LessonCreate,
    LessonOrderUpdate,
    LessonOrderUpdateList,
    LessonUpdate,
)
from app.services import lesson as service_lesson


async def create_lesson(
    db,
    *,
    section_id: int,
    title: str = "Test lesson",
    description: str | None = "Test lesson description",
    order: int = 0,
) -> Lesson:
    lesson = Lesson(
        section_id=section_id,
        title=title,
        description=description,
        order=order,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


@pytest.mark.asyncio
async def test_create_lesson_success(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson_info = LessonCreate(
        title="Python variables",
        description="Introduction to Python variables",
    )

    lesson = await service_lesson.create_lesson(
        section_id=section.id,
        lessonInfo=lesson_info,
        db=db,
    )

    assert lesson.id is not None
    assert lesson.section_id == section.id
    assert lesson.title == lesson_info.title
    assert lesson.description == lesson_info.description
    assert lesson.order == 0


@pytest.mark.asyncio
async def test_create_lesson_uses_next_order(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    await create_lesson(db, section_id=section.id, order=1)
    await create_lesson(db, section_id=section.id, order=4)
    lesson_info = LessonCreate(
        title="Next lesson",
        description="Description for the next lesson",
    )

    lesson = await service_lesson.create_lesson(
        section_id=section.id,
        lessonInfo=lesson_info,
        db=db,
    )

    assert lesson.order == 5


@pytest.mark.asyncio
async def test_create_lesson_section_not_found(db):
    lesson_info = LessonCreate(
        title="Test lesson",
        description="Test lesson description",
    )

    with pytest.raises(HTTPException) as exc:
        await service_lesson.create_lesson(
            section_id=999_999,
            lessonInfo=lesson_info,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Section not found"


@pytest.mark.asyncio
async def test_create_lesson_integrity_error(section_factory, db, monkeypatch):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson_info = LessonCreate(
        title="Test lesson",
        description="Test lesson description",
    )
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_lesson.create_lesson(
            section_id=section.id,
            lessonInfo=lesson_info,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == (
        "Failed to create lesson due to integrity error."
    )
    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_lessons_returns_lessons_in_order(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    other_section = await section_factory(
        course_id=section.course_id,
        is_published=False,
        order=1,
    )
    third = await create_lesson(db, section_id=section.id, order=2)
    first = await create_lesson(db, section_id=section.id, order=0)
    second = await create_lesson(db, section_id=section.id, order=1)
    await create_lesson(db, section_id=other_section.id, order=0)

    lessons = await service_lesson.get_lessons(
        section_id=section.id,
        db=db,
        check_course_published=False,
    )

    assert [lesson.id for lesson in lessons] == [
        first.id,
        second.id,
        third.id,
    ]


@pytest.mark.asyncio
async def test_get_lessons_returns_empty_list(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )

    lessons = await service_lesson.get_lessons(
        section_id=section.id,
        db=db,
        check_course_published=False,
    )

    assert lessons == []


@pytest.mark.asyncio
async def test_get_lessons_section_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_lesson.get_lessons(
            section_id=999_999,
            db=db,
            check_course_published=False,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Section not found"


@pytest.mark.asyncio
async def test_get_lessons_hides_draft_course(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    await create_lesson(db, section_id=section.id)

    with pytest.raises(HTTPException) as exc:
        await service_lesson.get_lessons(section_id=section.id, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_lessons_returns_lessons_for_published_course(
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)

    lessons = await service_lesson.get_lessons(
        section_id=section.id,
        db=db,
    )

    assert [item.id for item in lessons] == [lesson.id]


@pytest.mark.asyncio
async def test_get_lesson_success_for_published_course(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=True,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)

    result = await service_lesson.get_lesson(lesson_id=lesson.id, db=db)

    assert result.id == lesson.id


@pytest.mark.asyncio
async def test_get_lesson_returns_draft_when_course_check_disabled(
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)

    result = await service_lesson.get_lesson(
        lesson_id=lesson.id,
        db=db,
        check_course_published=False,
    )

    assert result.id == lesson.id


@pytest.mark.asyncio
async def test_get_lesson_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_lesson.get_lesson(
            lesson_id=999_999,
            db=db,
            check_course_published=False,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Lesson not found"


@pytest.mark.asyncio
async def test_get_lesson_section_not_found():
    lesson = SimpleNamespace(section_id=123)
    db = AsyncMock()
    db.get.side_effect = [lesson, None]

    with pytest.raises(HTTPException) as exc:
        await service_lesson.get_lesson(lesson_id=1, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Section not found"


@pytest.mark.asyncio
async def test_get_lesson_hides_lesson_from_draft_course(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)

    with pytest.raises(HTTPException) as exc:
        await service_lesson.get_lesson(lesson_id=lesson.id, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_delete_lesson_success(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    lesson_id = lesson.id

    await service_lesson.delete_lesson(lesson_id=lesson_id, db=db)

    assert await db.get(Lesson, lesson_id) is None


@pytest.mark.asyncio
async def test_delete_lesson_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_lesson.delete_lesson(lesson_id=999_999, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Lesson not found"


@pytest.mark.asyncio
async def test_delete_lesson_integrity_error(section_factory, db, monkeypatch):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_lesson.delete_lesson(lesson_id=lesson.id, db=db)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == (
        "Failed to delete lesson due to integrity error."
    )
    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_lesson_updates_only_provided_fields(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(
        db,
        section_id=section.id,
        title="Original lesson",
        description="Original lesson description",
        order=3,
    )

    updated_lesson = await service_lesson.update_lesson(
        lesson_id=lesson.id,
        lessonUpdate=LessonUpdate(title="Updated lesson"),
        db=db,
    )

    assert updated_lesson.id == lesson.id
    assert updated_lesson.section_id == section.id
    assert updated_lesson.title == "Updated lesson"
    assert updated_lesson.description == "Original lesson description"
    assert updated_lesson.order == 3


@pytest.mark.asyncio
async def test_update_lesson_can_clear_description(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(
        db,
        section_id=section.id,
        description="Original lesson description",
    )

    updated_lesson = await service_lesson.update_lesson(
        lesson_id=lesson.id,
        lessonUpdate=LessonUpdate(description=None),
        db=db,
    )

    assert updated_lesson.description is None


@pytest.mark.asyncio
async def test_update_lesson_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_lesson.update_lesson(
            lesson_id=999_999,
            lessonUpdate=LessonUpdate(title="Updated lesson"),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Lesson not found"


@pytest.mark.asyncio
async def test_update_lesson_integrity_error(section_factory, db, monkeypatch):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id)
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_lesson.update_lesson(
            lesson_id=lesson.id,
            lessonUpdate=LessonUpdate(title="Updated lesson"),
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == (
        "Failed to update lesson due to integrity error."
    )
    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_lesson_orders_success(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    first_lesson = await create_lesson(db, section_id=section.id, order=0)
    second_lesson = await create_lesson(db, section_id=section.id, order=1)
    order_list = LessonOrderUpdateList(
        lessons=[
            LessonOrderUpdate(id=first_lesson.id, order=1),
            LessonOrderUpdate(id=second_lesson.id, order=0),
        ]
    )

    result = await service_lesson.update_lesson_orders(
        order_list=order_list,
        db=db,
    )

    lessons_by_id = {lesson.id: lesson for lesson in result}
    assert set(lessons_by_id) == {first_lesson.id, second_lesson.id}
    assert lessons_by_id[first_lesson.id].order == 1
    assert lessons_by_id[second_lesson.id].order == 0
    assert (await db.get(Lesson, first_lesson.id)).order == 1
    assert (await db.get(Lesson, second_lesson.id)).order == 0


@pytest.mark.asyncio
async def test_update_lesson_orders_duplicate_lesson_ids(db):
    order_list = LessonOrderUpdateList(
        lessons=[
            LessonOrderUpdate(id=1, order=0),
            LessonOrderUpdate(id=1, order=1),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await service_lesson.update_lesson_orders(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Duplicate lesson IDs found"


@pytest.mark.asyncio
async def test_update_lesson_orders_duplicate_order_values(db):
    order_list = LessonOrderUpdateList(
        lessons=[
            LessonOrderUpdate(id=1, order=0),
            LessonOrderUpdate(id=2, order=0),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await service_lesson.update_lesson_orders(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Duplicate order values found"


@pytest.mark.asyncio
async def test_update_lesson_orders_lessons_from_different_sections(
    section_factory,
    db,
):
    first_section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    second_section = await section_factory(
        course_id=first_section.course_id,
        is_published=False,
        order=1,
    )
    first_lesson = await create_lesson(
        db,
        section_id=first_section.id,
        order=0,
    )
    second_lesson = await create_lesson(
        db,
        section_id=second_section.id,
        order=0,
    )
    order_list = LessonOrderUpdateList(
        lessons=[
            LessonOrderUpdate(id=first_lesson.id, order=0),
            LessonOrderUpdate(id=second_lesson.id, order=1),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await service_lesson.update_lesson_orders(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "All lessons must belong to the same section"


@pytest.mark.asyncio
async def test_update_lesson_orders_integrity_error(
    section_factory,
    db,
    monkeypatch,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id, order=0)
    order_list = LessonOrderUpdateList(
        lessons=[LessonOrderUpdate(id=lesson.id, order=1)]
    )
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_lesson.update_lesson_orders(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == (
        "Failed to update lesson orders due to integrity error"
    )
    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_lesson_orders_empty_list(db):
    result = await service_lesson.update_lesson_orders(
        order_list=LessonOrderUpdateList(lessons=[]),
        db=db,
    )

    assert result == []


@pytest.mark.asyncio
async def test_update_lesson_orders_ignores_unknown_lesson_id(
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    lesson = await create_lesson(db, section_id=section.id, order=0)
    unknown_lesson_id = lesson.id + 999_999
    order_list = LessonOrderUpdateList(
        lessons=[
            LessonOrderUpdate(id=lesson.id, order=1),
            LessonOrderUpdate(id=unknown_lesson_id, order=2),
        ]
    )

    result = await service_lesson.update_lesson_orders(
        order_list=order_list,
        db=db,
    )

    assert [item.id for item in result] == [lesson.id]
    assert (await db.get(Lesson, lesson.id)).order == 1
    assert await db.get(Lesson, unknown_lesson_id) is None
