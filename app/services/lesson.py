from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from app.schemas.lesson import LessonCreate, LessonUpdate, LessonOrderUpdate, LessonOrderUpdateList
from app.models import Section, Lesson, Course


async def create_lesson(section_id: int, lessonInfo: LessonCreate, db: AsyncSession):
    parent_and_order = (
        await db.execute(
            select(Section.id, func.max(Lesson.order))
            .outerjoin(Lesson, Lesson.section_id == Section.id)
            .where(Section.id == section_id)
            .group_by(Section.id)
        )
    ).one_or_none()
    if parent_and_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    
    _, max_order = parent_and_order
    order = 0 if max_order is None else max_order + 1
    new_lesson = Lesson(
        section_id=section_id,
        title=lessonInfo.title,
        description=lessonInfo.description,
        order=order
    )
    db.add(new_lesson)
    
    try:
        await db.commit()
        return new_lesson
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create lesson due to integrity error."
        )
        
        
async def get_lessons(section_id: int, db: AsyncSession, check_course_published: bool = True) -> list[Lesson]:
    if check_course_published:
        row = (
            await db.execute(
                select(Section, Course.is_published)
                .outerjoin(Course, Course.id == Section.course_id)
                .where(Section.id == section_id)
            )
        ).one_or_none()
        section, course_is_published = row if row else (None, None)
    else:
        section = await db.get(Section, section_id)
        course_is_published = None

    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    
    if check_course_published:
        if not course_is_published:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
    
    result = await db.execute(
        select(Lesson)
            .where(Lesson.section_id == section_id)
            .order_by(Lesson.order)
    )
    lessons = result.scalars().all()
    return lessons # type: ignore


async def get_lesson(lesson_id: int, db: AsyncSession, check_course_published: bool = True) -> Lesson:
    if check_course_published:
        row = (
            await db.execute(
                select(Lesson, Section.id, Course.is_published)
                .outerjoin(Section, Section.id == Lesson.section_id)
                .outerjoin(Course, Course.id == Section.course_id)
                .where(Lesson.id == lesson_id)
            )
        ).one_or_none()
        lesson, section_id, course_is_published = (
            row if row else (None, None, None)
        )
    else:
        lesson = await db.get(Lesson, lesson_id)
        section_id = course_is_published = None

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    if check_course_published:
        if section_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found"
            )
        if not course_is_published:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found"
            )
    
    return lesson


async def delete_lesson(lesson_id: int, db: AsyncSession):
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    try:
        await db.delete(lesson)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete lesson due to integrity error."
        )
        
        
async def update_lesson(lesson_id: int, lessonUpdate: LessonUpdate, db: AsyncSession) -> Lesson:
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    for field, value in lessonUpdate.model_dump(exclude_unset=True).items():
        setattr(lesson, field, value)
    
    try:
        await db.commit()
        return lesson
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update lesson due to integrity error."
        )
        

async def update_lesson_orders(order_list: LessonOrderUpdateList, db: AsyncSession) -> list[Lesson]:
    lessons_ids = [item.id for item in order_list.lessons]
    if len(lessons_ids) != len(set(lessons_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate lesson IDs found"
        )
    # check for duplicate order values
    order_values = [item.order for item in order_list.lessons]
    if len(order_values) != len(set(order_values)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate order values found"
        )
    lessons = await db.execute(
        select(Lesson)
            .where(Lesson.id.in_(lessons_ids))
    )
    scalar_lessons = lessons.scalars().all()
    section_ids = {lesson.section_id for lesson in scalar_lessons}
    if len(section_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All lessons must belong to the same section"
        )
    new_orders = {item.id: item.order for item in order_list.lessons}
    for lesson in scalar_lessons:
        lesson.order = new_orders[lesson.id]
    try:
        await db.commit()
        return scalar_lessons # type: ignore
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update lesson orders due to integrity error"
        )
