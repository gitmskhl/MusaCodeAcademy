from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models import Section
from app.schemas.section import SectionCreate, SectionUpdate, SectionOrderUpdateList, SectionOrderUpdate
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


@pytest.mark.asyncio
async def test_update_section_success(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0
    )
    updated_section = await service_section.update_section(
        section_id=section.id,
        sectionUpdate=SectionUpdate(title="New title", description="New description"),
        db=db
    )
    
    assert updated_section.id == section.id
    assert updated_section.course_id == section.course_id
    assert updated_section.order == 0
    assert updated_section.title == "New title"
    assert updated_section.description == "New description"
    
   
@pytest.mark.asyncio
async def test_update_section_success_title(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0
    )
    updated_section = await service_section.update_section(
        section_id=section.id,
        sectionUpdate=SectionUpdate(title="New title"),
        db=db
    )
    
    assert updated_section.id == section.id
    assert updated_section.course_id == section.course_id
    assert updated_section.order == 0
    assert updated_section.title == "New title"
    assert updated_section.description == section.description
   
   
@pytest.mark.asyncio
async def test_update_section_success_description(section_factory, db):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0
    )
    updated_section = await service_section.update_section(
        section_id=section.id,
        sectionUpdate=SectionUpdate(description="New description"),
        db=db
    )
    
    assert updated_section.id == section.id
    assert updated_section.course_id == section.course_id
    assert updated_section.order == 0
    assert updated_section.title == section.title
    assert updated_section.description ==    "New description"

    
@pytest.mark.asyncio
async def test_update_section_section_not_exists(db):
    updatedSection = SectionUpdate(title="New title", description="New description")
    with pytest.raises(HTTPException) as exc:
        await service_section.update_section(
            section_id=0,
            sectionUpdate=updatedSection,
            db=db
        )
    
    assert exc.value.status_code == status.HTTP_404_NOT_FOUND
    assert exc.value.detail == "Section not found"
    

@pytest.mark.asyncio
async def test_update_section_integrity_error(section_factory, db, monkeypatch):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0
    )
    updatedSection = SectionUpdate(title="New title", description="New description")
    
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_section.update_section(
            section_id=section.id,
            sectionUpdate=updatedSection,
            db=db
        )

    assert exc.value.status_code == status.HTTP_409_CONFLICT
    assert exc.value.detail == (
        "Failed to update section due to integrity error"
    )
    rollback_mock.assert_awaited_once()
    
    
@pytest.mark.asyncio
async def test_update_section_orders_success(section_factory, db):
    section1 = await section_factory(
        course_id=None,
        is_published=False,
        order=0
    )
    section2 = await section_factory(
        course_id=section1.course_id,
        is_published=False,
        order=1
    )
    
    order_list = SectionOrderUpdateList(
        sections=[
            SectionOrderUpdate(id=section1.id, order=1),
            SectionOrderUpdate(id=section2.id, order=0)
        ]
    )
    
    await service_section.update_section_orders(order_list=order_list, db=db)
    
    updated_section1 = await db.get(Section, section1.id)
    updated_section2 = await db.get(Section, section2.id)
    
    assert updated_section1.order == 1
    assert updated_section2.order == 0


@pytest.mark.asyncio
async def test_update_section_orders_duplicate_section_ids(db):
    order_list = SectionOrderUpdateList(
        sections=[
            SectionOrderUpdate(id=1, order=0),
            SectionOrderUpdate(id=1, order=1),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await service_section.update_section_orders(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Duplicate section IDs found"


@pytest.mark.asyncio
async def test_update_section_orders_duplicate_order_values(db):
    order_list = SectionOrderUpdateList(
        sections=[
            SectionOrderUpdate(id=1, order=0),
            SectionOrderUpdate(id=2, order=0),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await service_section.update_section_orders(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "Duplicate order values found"


@pytest.mark.asyncio
async def test_update_section_orders_sections_from_different_courses(
    section_factory,
    db,
):
    first_section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    second_section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    order_list = SectionOrderUpdateList(
        sections=[
            SectionOrderUpdate(id=first_section.id, order=0),
            SectionOrderUpdate(id=second_section.id, order=1),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        await service_section.update_section_orders(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == "All sections must belong to the same course"


@pytest.mark.asyncio
async def test_update_section_orders_integrity_error(
    section_factory,
    db,
    monkeypatch,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    order_list = SectionOrderUpdateList(
        sections=[
            SectionOrderUpdate(id=section.id, order=1),
        ]
    )
    commit_mock = AsyncMock(
        side_effect=IntegrityError("forced error", {}, Exception("forced error"))
    )
    rollback_mock = AsyncMock()
    monkeypatch.setattr(db, "commit", commit_mock)
    monkeypatch.setattr(db, "rollback", rollback_mock)

    with pytest.raises(HTTPException) as exc:
        await service_section.update_section_orders(
            order_list=order_list,
            db=db,
        )

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.detail == (
        "Failed to update section orders due to integrity error"
    )
    commit_mock.assert_awaited_once()
    rollback_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_section_orders_empty_list(db):
    order_list = SectionOrderUpdateList(sections=[])

    result = await service_section.update_section_orders(
        order_list=order_list,
        db=db,
    )

    assert result == []


@pytest.mark.asyncio
async def test_update_section_orders_ignores_unknown_section_id(
    section_factory,
    db,
):
    section = await section_factory(
        course_id=None,
        is_published=False,
        order=0,
    )
    unknown_section_id = section.id + 999_999
    order_list = SectionOrderUpdateList(
        sections=[
            SectionOrderUpdate(id=section.id, order=1),
            SectionOrderUpdate(id=unknown_section_id, order=2),
        ]
    )

    await service_section.update_section_orders(
        order_list=order_list,
        db=db,
    )

    updated_section = await db.get(Section, section.id)
    assert updated_section.order == 1
    assert await db.get(Section, unknown_section_id) is None
    
