from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Course, Enrollment

async def enroll(course_id: int, user_id: int, db: AsyncSession) -> Enrollment:
    course = await db.get(Course, course_id)
    if not course or not course.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    result = await db.execute(
        select(Enrollment)
        .where(and_(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id
        ))
    )
    enrollment = result.scalar_one_or_none()
    if enrollment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this course."
        )
    new_enrollment = Enrollment(
        user_id=user_id,
        course_id=course_id
    )

    db.add(new_enrollment)
    await db.commit()
    await db.refresh(new_enrollment)
    return new_enrollment




async def get_user_enrollments(user_id: int, db: AsyncSession) -> list[Enrollment]:
    result = await db.execute(
        select(Enrollment)
        .options(selectinload(Enrollment.course))
        .where(Enrollment.user_id == user_id)
        .order_by(Enrollment.created_at.desc())
    )
    return list(result.scalars().all())


async def is_user_enrolled(course_id: int, user_id: int, db: AsyncSession) -> bool:
    result = await db.execute(
        select(Enrollment.id)
        .where(and_(
            Enrollment.course_id == course_id,
            Enrollment.user_id == user_id
        ))
    )
    return result.scalar_one_or_none() is not None
