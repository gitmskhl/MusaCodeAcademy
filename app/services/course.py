from typing import Sequence
from fastapi import status, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate
from app.api.dependencies import DBSession


async def course_exists_by_slug(slug: str, db: DBSession) -> bool:
    result = await db.execute(
        select(Course)
            .where(func.lower(Course.slug) == slug.lower())
    )
    course = result.scalars().first()
    return True if course else False


async def create_course(courseInfo: CourseCreate, db: DBSession) -> Course:
    
    result = await db.execute(
        select(Course)
        .where(func.lower(Course.slug) == courseInfo.slug.lower())
    )
    
    course = result.scalars().first()
    if course:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course with this slug already exists"
        )
    
    new_course = Course(
        title=courseInfo.title,
        slug=courseInfo.slug.lower(),
        short_description=courseInfo.short_description,
        description=courseInfo.description
    )
    db.add(new_course)
    
    try:
        await db.commit()
        await db.refresh(new_course)
        return new_course
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course with this slug already exists"
        )


async def get_published_courses(db: DBSession) -> Sequence[Course]:
    result = await db.execute(select(Course).where(Course.is_published == True))
    return result.scalars().all()


async def get_all_courses(db: DBSession) -> Sequence[Course]:
    result = await db.execute(select(Course))
    return result.scalars().all()


async def update_course(course_id: int, updateInfo: CourseUpdate, db: DBSession) -> Course:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    if updateInfo.slug is not None and course.slug != updateInfo.slug.lower():
        if (await course_exists_by_slug(updateInfo.slug, db)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Course with this slug already exists"
            )
    update_data = updateInfo.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'slug':
            course.slug = value.lower()
        else:
            setattr(course, field, value)
    
    try:
        await db.commit()
        await db.refresh(course)
        return course
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Course with this slug already exists"
            )