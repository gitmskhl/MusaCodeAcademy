from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Course, CourseActivity, Lesson, Section, Step


async def record_course_visit(
    *,
    step_id: int,
    course_slug: str,
    user_id: int,
    db: AsyncSession,
) -> CourseActivity | None:
    result = await db.execute(
        select(Course.id)
        .join(Section, Section.course_id == Course.id)
        .join(Lesson, Lesson.section_id == Section.id)
        .join(Step, Step.lesson_id == Lesson.id)
        .where(
            Step.id == step_id,
            Course.slug == course_slug.lower(),
            Course.is_published.is_(True),
        )
    )
    course_id = result.scalar_one_or_none()
    if course_id is None:
        return None

    activity_result = await db.execute(
        select(CourseActivity).where(
            and_(
                CourseActivity.course_id == course_id,
                CourseActivity.user_id == user_id,
            )
        )
    )
    activity = activity_result.scalar_one_or_none()
    now = datetime.now(UTC)

    if activity is None:
        activity = CourseActivity(
            user_id=user_id,
            course_id=course_id,
            last_step_id=step_id,
            last_visited_at=now,
        )
        db.add(activity)
    else:
        activity.last_step_id = step_id
        activity.last_visited_at = now

    await db.commit()
    await db.refresh(activity)
    return activity
