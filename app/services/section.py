from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.api.dependencies import DBSession
from app.models import Section, Course
from app.schemas.section import SectionCreate, SectionUpdate, SectionOrderUpdateList

async def get_course_sections(course_id: int, db: AsyncSession, check_published: bool) -> list[Section]:
    is_published = await db.scalar(
        select(Course.is_published).where(Course.id == course_id)
    )
    if is_published is None or (check_published and not is_published):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    result = await db.execute(
        select(Section)
            .where(Section.course_id == course_id)
            .order_by(Section.order)
    )
    return result.scalars().all() # type: ignore


async def create_course_section(
    course_id: int,
    sectionInfo: SectionCreate,
    db: DBSession
) -> Section:
    parent_and_order = (
        await db.execute(
            select(Course.id, func.max(Section.order))
            .outerjoin(Section, Section.course_id == Course.id)
            .where(Course.id == course_id)
            .group_by(Course.id)
        )
    ).one_or_none()
    if parent_and_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    _, max_order = parent_and_order
    order = 0 if max_order is None else max_order + 1
    new_section = Section(
        course_id = course_id,
        title = sectionInfo.title,
        description = sectionInfo.description,
        order = order
    )
    db.add(new_section)
    
    try:
        await db.commit()
        return new_section
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create section due to integrity error"
        )
        

async def get_section(section_id: int, db: AsyncSession, check_course: bool) -> Section:
    if not check_course:
        section = await db.get(Section, section_id)
        course_is_published = None
    else:
        row = (
            await db.execute(
                select(Section, Course.is_published)
                .outerjoin(Course, Course.id == Section.course_id)
                .where(Section.id == section_id)
            )
        ).one_or_none()
        section, course_is_published = row if row else (None, None)

    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    if check_course:
        if not course_is_published:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
    return section


async def delete_section(section_id: int, db: AsyncSession):
    section = await db.get(Section, section_id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    try:
        await db.delete(section)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete section due to integrity error"
        )
        

async def update_section(section_id: int, sectionUpdate: SectionUpdate, db: AsyncSession):
    section = await db.get(Section, section_id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    
    update_data = sectionUpdate.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(section, field, value)
    
    try:
        await db.commit()
        return section
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to update section due to integrity error"
            )
        
        
async def update_section_orders(order_list: SectionOrderUpdateList, db: AsyncSession):
    # check for duplicate section ids
    section_ids = [item.id for item in order_list.sections]
    if len(section_ids) != len(set(section_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate section IDs found"
        )
    # check for duplicate order values
    order_values = [item.order for item in order_list.sections]
    if len(order_values) != len(set(order_values)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate order values found"
        )
    sections = await db.execute(
        select(Section)
            .where(Section.id.in_(section_ids))
    )
    scalar_sections = sections.scalars().all()
    course_ids = {section.course_id for section in scalar_sections}
    if len(course_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All sections must belong to the same course"
        )
    new_orders = {item.id: item.order for item in order_list.sections}
    for section in scalar_sections:
        section.order = new_orders[section.id]
    try:
        await db.commit()
        return scalar_sections
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update section orders due to integrity error"
        )
