from typing import Sequence
from fastapi import status, HTTPException
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.models.course import Course
from app.models.section import Section
from app.schemas.course import CourseCreate, CourseUpdate, CourseInfo
from app.api.dependencies import DBSession


async def course_exists_by_slug(slug: str, db: DBSession) -> bool:
    return bool(
        await db.scalar(
            select(exists().where(Course.slug == slug.lower()))
        )
    )


async def create_course(courseInfo: CourseCreate, db: DBSession) -> Course:
    normalized_slug = courseInfo.slug.lower()

    result = await db.execute(
        select(Course)
        .where(Course.slug == normalized_slug)
    )
    
    course = result.scalars().first()
    if course:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course with this slug already exists"
        )
    
    new_course = Course(
        title=courseInfo.title,
        slug=normalized_slug,
        short_description=courseInfo.short_description,
        description=courseInfo.description,
        level=courseInfo.level,
        price_label=courseInfo.price_label,
        outcomes=courseInfo.outcomes,
    )
    db.add(new_course)
    
    try:
        await db.commit()
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


async def get_published_course_info(course_id: int, db: DBSession) -> Course:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    if not course.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Course is not published"
        )
    return course


async def get_course_info(course_id: int, db: DBSession) -> Course:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return course


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
        return course
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Course with this slug already exists"
            )
        
        
async def delete_course(course_id: int, db: DBSession):
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    try:
        await db.delete(course)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the course"
        )


def build_course_info(course: Course) -> CourseInfo:
    course_info = CourseInfo.model_validate(course)
    sections = list(course_info.sections)

    course_info.sections_count = len(sections)
    course_info.lessons_count = sum(len(section.lessons) for section in sections)

    return course_info


async def get_published_course_page(course_slug: str, db: DBSession) -> CourseInfo:
    result = await db.execute(
        select(Course)
        .options(
            selectinload(Course.sections)
            .selectinload(Section.lessons)
        )
        .where(
            Course.slug == course_slug.lower(),
            Course.is_published == True
        )
    )
    course = result.scalars().first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    return build_course_info(course)
