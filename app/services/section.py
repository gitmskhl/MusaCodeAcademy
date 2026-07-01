from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.api.dependencies import DBSession
from app.models import Section, Course
from app.schemas.section import SectionCreate, SectionUpdate

async def get_course_sections(course_id: int, db: AsyncSession, check_published: bool) -> list[Section]:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    if check_published and not course.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    result = await db.execute(
        select(Section)
            .where(Section.course_id == course_id)
            .order_by(Section.order)
    )
    return list(result.scalars().all())


async def create_course_section(
    course_id: int,
    sectionInfo: SectionCreate,
    db: DBSession
) -> Section:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    max_order = await db.scalar(
        select(func.max(Section.order))
            .where(Section.course_id == course_id)
    )
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
        await db.refresh(new_section)
        return new_section
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create section due to integrity error"
        )
        

async def get_section(section_id: int, db: AsyncSession, check_course: bool) -> Section:
    section = await db.get(Section, section_id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    if check_course:
        course = await db.get(Course, section.course_id)
        if not course or not course.is_published:
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
    course = await db.get(Course, section.course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    update_data = sectionUpdate.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(section, field, value)
    
    try:
        await db.commit()
        await db.refresh(section)
        return section
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to update section due to integrity error"
            )