from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models import Lesson, Section
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate
from app.services import course as service_course


async def create_section(
    db,
    *,
    course_id: int,
    title: str = "Test section",
    description: str | None = "Test section description",
    order: int = 0,
) -> Section:
    section = Section(
        course_id=course_id,
        title=title,
        description=description,
        order=order,
    )
    db.add(section)
    await db.commit()
    await db.refresh(section)
    return section


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
async def test_create_course_success(db):
    course_info = CourseCreate(
        title="Python basics",
        short_description="Python basics",
        description="A complete introductory Python programming course.",
        slug="Python",
    )

    course = await service_course.create_course(courseInfo=course_info, db=db)

    assert course.id is not None
    assert course.title == course_info.title
    assert course.short_description == course_info.short_description
    assert course.description == course_info.description
    assert course.slug == course_info.slug.lower()
    assert course.is_published is False


@pytest.mark.asyncio
async def test_create_course_slug_exists_case_insensitive(course_factory, db):
    await course_factory(slug="pypy")
    course_info = CourseCreate(
        title="Python for someone",
        short_description="Python basics",
        description="A complete introductory Python programming course.",
        slug="PyPy",
    )

    with pytest.raises(HTTPException) as exc:
        await service_course.create_course(courseInfo=course_info, db=db)

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == "Course with this slug already exists"


@pytest.mark.asyncio
async def test_create_course_integrity_error_returns_conflict(db, monkeypatch):
    course_info = CourseCreate(
        title="Python basics",
        short_description="Python basics",
        description="A complete introductory Python programming course.",
        slug="python",
    )
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_course.create_course(courseInfo=course_info, db=db)

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == "Course with this slug already exists"
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_course_exists_by_slug_returns_false(db):
    result = await service_course.course_exists_by_slug(slug="python", db=db)

    assert result is False


@pytest.mark.asyncio
async def test_course_exists_by_slug_returns_true_case_insensitive(
    course_factory,
    db,
):
    await course_factory(slug="python")

    result = await service_course.course_exists_by_slug(slug="PYTHON", db=db)

    assert result is True


@pytest.mark.asyncio
async def test_get_published_courses_returns_empty_list(db):
    courses = await service_course.get_published_courses(db)

    assert courses == []


@pytest.mark.asyncio
async def test_get_published_courses_returns_only_published(
    course_factory,
    db,
):
    published_first = await course_factory(
        slug="published-first",
        is_published=True,
    )
    published_second = await course_factory(
        slug="published-second",
        is_published=True,
    )
    await course_factory(slug="draft", is_published=False)

    courses = await service_course.get_published_courses(db)

    assert {course.id for course in courses} == {
        published_first.id,
        published_second.id,
    }
    assert all(course.is_published for course in courses)


@pytest.mark.asyncio
async def test_get_all_courses_returns_empty_list(db):
    courses = await service_course.get_all_courses(db)

    assert courses == []


@pytest.mark.asyncio
async def test_get_all_courses_returns_published_and_drafts(
    course_factory,
    db,
):
    published = await course_factory(slug="published", is_published=True)
    draft = await course_factory(slug="draft", is_published=False)

    courses = await service_course.get_all_courses(db)

    assert {course.id for course in courses} == {published.id, draft.id}


@pytest.mark.asyncio
async def test_get_published_course_info_success(course_factory, db):
    course = await course_factory(slug="published", is_published=True)

    result = await service_course.get_published_course_info(course.id, db)

    assert result.id == course.id


@pytest.mark.asyncio
async def test_get_published_course_info_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_course.get_published_course_info(999_999, db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_published_course_info_rejects_draft(course_factory, db):
    course = await course_factory(slug="draft", is_published=False)

    with pytest.raises(HTTPException) as exc:
        await service_course.get_published_course_info(course.id, db)

    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Course is not published"


@pytest.mark.asyncio
async def test_get_published_course_page_returns_course_sections_and_lessons(
    course_factory,
    db,
):
    course = await course_factory(
        slug="python-basics",
        title="Python basics",
        is_published=True,
    )
    second_section = await create_section(
        db,
        course_id=course.id,
        title="Second section",
        order=1,
    )
    first_section = await create_section(
        db,
        course_id=course.id,
        title="First section",
        order=0,
    )
    second_lesson = await create_lesson(
        db,
        section_id=first_section.id,
        title="Second lesson",
        order=1,
    )
    first_lesson = await create_lesson(
        db,
        section_id=first_section.id,
        title="First lesson",
        order=0,
    )
    await create_lesson(
        db,
        section_id=second_section.id,
        title="Another lesson",
        order=0,
    )

    result = await service_course.get_published_course_page(
        course_slug="PYTHON-BASICS",
        db=db,
    )

    assert result.id == course.id
    assert result.title == "Python basics"
    assert result.slug == "python-basics"
    assert [section.id for section in result.sections] == [
        first_section.id,
        second_section.id,
    ]
    assert [lesson.id for lesson in result.sections[0].lessons] == [
        first_lesson.id,
        second_lesson.id,
    ]
    assert result.sections[0].lessons[0].title == "First lesson"


@pytest.mark.asyncio
async def test_get_published_course_page_returns_empty_sections(
    course_factory,
    db,
):
    course = await course_factory(slug="empty-course", is_published=True)

    result = await service_course.get_published_course_page(
        course_slug=course.slug,
        db=db,
    )

    assert result.id == course.id
    assert result.sections == []


@pytest.mark.asyncio
async def test_get_published_course_page_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_course.get_published_course_page(
            course_slug="missing-course",
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_published_course_page_hides_draft(course_factory, db):
    await course_factory(slug="draft-course", is_published=False)

    with pytest.raises(HTTPException) as exc:
        await service_course.get_published_course_page(
            course_slug="draft-course",
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_course_info_returns_draft(course_factory, db):
    course = await course_factory(slug="draft", is_published=False)

    result = await service_course.get_course_info(course.id, db)

    assert result.id == course.id


@pytest.mark.asyncio
async def test_get_course_info_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_course.get_course_info(999_999, db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_update_course_updates_only_provided_fields(course_factory, db):
    course = await course_factory(
        slug="python",
        title="Python basics",
        is_published=False,
    )
    original_description = course.description
    update_info = CourseUpdate(
        title="Advanced Python",
        is_published=True,
    )

    updated_course = await service_course.update_course(
        course_id=course.id,
        updateInfo=update_info,
        db=db,
    )

    assert updated_course.title == "Advanced Python"
    assert updated_course.is_published is True
    assert updated_course.slug == "python"
    assert updated_course.description == original_description


@pytest.mark.asyncio
async def test_update_course_normalizes_slug(course_factory, db):
    course = await course_factory(slug="python")
    update_info = CourseUpdate(slug="FastAPI")

    updated_course = await service_course.update_course(
        course_id=course.id,
        updateInfo=update_info,
        db=db,
    )

    assert updated_course.slug == "fastapi"


@pytest.mark.asyncio
async def test_update_course_allows_same_slug_with_different_case(
    course_factory,
    db,
):
    course = await course_factory(slug="python")
    update_info = CourseUpdate(slug="PYTHON")

    updated_course = await service_course.update_course(
        course_id=course.id,
        updateInfo=update_info,
        db=db,
    )

    assert updated_course.slug == "python"


@pytest.mark.asyncio
async def test_update_course_duplicate_slug_returns_conflict(
    course_factory,
    db,
):
    course = await course_factory(slug="python")
    await course_factory(slug="fastapi")
    update_info = CourseUpdate(slug="FASTAPI")

    with pytest.raises(HTTPException) as exc:
        await service_course.update_course(
            course_id=course.id,
            updateInfo=update_info,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == "Course with this slug already exists"


@pytest.mark.asyncio
async def test_update_course_not_found(db):
    update_info = CourseUpdate(title="Advanced Python")

    with pytest.raises(HTTPException) as exc:
        await service_course.update_course(
            course_id=999_999,
            updateInfo=update_info,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_update_course_integrity_error_returns_conflict(
    course_factory,
    db,
    monkeypatch,
):
    course = await course_factory(slug="python")
    update_info = CourseUpdate(title="Advanced Python")
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_course.update_course(
            course_id=course.id,
            updateInfo=update_info,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == "Course with this slug already exists"
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_course_success(course_factory, db):
    course = await course_factory(slug="course-to-delete")
    course_id = course.id

    await service_course.delete_course(course_id, db)

    assert await db.get(Course, course_id) is None


@pytest.mark.asyncio
async def test_delete_course_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_course.delete_course(999_999, db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_delete_course_database_error_returns_internal_server_error(
    course_factory,
    db,
    monkeypatch,
):
    course = await course_factory(slug="course-to-delete")
    commit_mock = AsyncMock(side_effect=Exception("forced error"))
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_course.delete_course(course.id, db)

    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc.value.detail == "An error occurred while deleting the course"
    rollback_mock.assert_awaited_once()
