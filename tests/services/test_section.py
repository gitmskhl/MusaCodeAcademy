from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models import Section
from app.schemas.section import SectionCreate
from app.services import section as service_section


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


@pytest.mark.asyncio
async def test_get_course_sections_returns_sections_in_order(real_course, db):
    third = await create_section(db, course_id=real_course.id, order=2)
    first = await create_section(db, course_id=real_course.id, order=0)
    second = await create_section(db, course_id=real_course.id, order=1)

    sections = await service_section.get_course_sections(
        course_id=real_course.id,
        db=db,
        check_published=False,
    )

    assert [section.id for section in sections] == [
        first.id,
        second.id,
        third.id,
    ]


@pytest.mark.asyncio
async def test_get_course_sections_returns_empty_list(real_course, db):
    sections = await service_section.get_course_sections(
        course_id=real_course.id,
        db=db,
        check_published=False,
    )

    assert sections == []


@pytest.mark.asyncio
async def test_get_course_sections_course_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_section.get_course_sections(
            course_id=999_999,
            db=db,
            check_published=False,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_course_sections_hides_draft_course(real_course, db):
    await create_section(db, course_id=real_course.id)

    with pytest.raises(HTTPException) as exc:
        await service_section.get_course_sections(
            course_id=real_course.id,
            db=db,
            check_published=True,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_get_course_sections_returns_published_course(real_course, db):
    real_course.is_published = True
    section = await create_section(db, course_id=real_course.id)

    sections = await service_section.get_course_sections(
        course_id=real_course.id,
        db=db,
        check_published=True,
    )

    assert [item.id for item in sections] == [section.id]


@pytest.mark.asyncio
async def test_create_course_section_success(real_course, section_data, db):
    section_info = SectionCreate(
        title=section_data["title"],
        description=section_data["description"],
    )

    section = await service_section.create_course_section(
        course_id=real_course.id,
        sectionInfo=section_info,
        db=db,
    )

    assert section.id is not None
    assert section.course_id == real_course.id
    assert section.title == section_data["title"]
    assert section.description == section_data["description"]
    assert section.order == 0


@pytest.mark.asyncio
async def test_create_course_section_course_not_found(section_data, db):
    section_info = SectionCreate(
        title=section_data["title"],
        description=section_data["description"],
    )

    with pytest.raises(HTTPException) as exc:
        await service_section.create_course_section(
            course_id=999_999,
            sectionInfo=section_info,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_create_course_section_uses_next_order(real_course, db):
    existing = await create_section(
        db,
        course_id=real_course.id,
        order=3,
    )
    section_info = SectionCreate(
        title="Next section",
        description="Next section description",
    )

    section = await service_section.create_course_section(
        course_id=real_course.id,
        sectionInfo=section_info,
        db=db,
    )

    assert existing.order == 3
    assert section.order == 4


@pytest.mark.asyncio
async def test_create_course_section_integrity_error(real_course, db, monkeypatch):
    section_info = SectionCreate(
        title="Test section",
        description="Test section description",
    )
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_section.create_course_section(
            course_id=real_course.id,
            sectionInfo=section_info,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == (
        "Failed to create section due to integrity error"
    )
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_section_success_for_published_course(real_course, db):
    real_course.is_published = True
    section = await create_section(db, course_id=real_course.id)

    result = await service_section.get_section(
        section_id=section.id,
        db=db,
        check_course=True,
    )

    assert result.id == section.id


@pytest.mark.asyncio
async def test_get_section_returns_draft_when_course_check_disabled(
    real_course,
    db,
):
    section = await create_section(db, course_id=real_course.id)

    result = await service_section.get_section(
        section_id=section.id,
        db=db,
        check_course=False,
    )

    assert result.id == section.id


@pytest.mark.asyncio
async def test_get_section_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_section.get_section(
            section_id=999_999,
            db=db,
            check_course=False,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Section not found"


@pytest.mark.asyncio
async def test_get_section_hides_section_from_draft_course(real_course, db):
    section = await create_section(db, course_id=real_course.id)

    with pytest.raises(HTTPException) as exc:
        await service_section.get_section(
            section_id=section.id,
            db=db,
            check_course=True,
        )

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Course not found"


@pytest.mark.asyncio
async def test_delete_section_success(real_course, db):
    section = await create_section(db, course_id=real_course.id)
    section_id = section.id

    await service_section.delete_section(section_id=section_id, db=db)

    assert await db.get(Section, section_id) is None


@pytest.mark.asyncio
async def test_delete_section_not_found(db):
    with pytest.raises(HTTPException) as exc:
        await service_section.delete_section(section_id=999_999, db=db)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Section not found"


@pytest.mark.asyncio
async def test_delete_section_integrity_error(real_course, db, monkeypatch):
    section = await create_section(db, course_id=real_course.id)
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_section.delete_section(section_id=section.id, db=db)

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == (
        "Failed to delete section due to integrity error"
    )
    rollback_mock.assert_awaited_once()
