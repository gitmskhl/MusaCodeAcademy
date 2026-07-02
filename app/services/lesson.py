from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from app.schemas.lesson import LessonCreate, LessonUpdate
from app.models import Section, Lesson, Course


async def create_lesson(section_id: int, lessonInfo: LessonCreate, db: AsyncSession):

    section = await db.get(Section, section_id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    
    max_order = await db.scalar(
        select(func.max(Lesson.order))
            .where(Lesson.section_id == section_id)
    )
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
        await db.refresh(new_lesson)
        return new_lesson
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create lesson due to integrity error."
        )
        
        
async def get_lessons(section_id: int, db: AsyncSession, check_course_published: bool = True) -> list[Lesson]:
    section = await db.get(Section, section_id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found"
        )
    
    if check_course_published:
        course = await db.get(Course, section.course_id)
        if not course or not course.is_published:
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
    return list(lessons)


async def get_lesson(lesson_id: int, db: AsyncSession, check_course_published: bool = True) -> Lesson:
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    if check_course_published:
        section = await db.get(Section, lesson.section_id)
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found"
            )
        course = await db.get(Course, section.course_id)
        if not course or not course.is_published:
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
    
    for field, value in lessonUpdate.dict(exclude_unset=True).items():
        setattr(lesson, field, value)
    
    try:
        await db.commit()
        await db.refresh(lesson)
        return lesson
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update lesson due to integrity error."
        )