from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Course, Enrollment, Lesson, Section, Step, StepProgress
from app.schemas.progress import (
    CourseSectionsProgress,
    LessonProgress,
    SectionProgress,
)


async def _get_step_course_id(step_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(Course.id, Course.is_published)
        .join(Section, Section.course_id == Course.id)
        .join(Lesson, Lesson.section_id == Section.id)
        .join(Step, Step.lesson_id == Lesson.id)
        .where(Step.id == step_id)
    )
    row = result.one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found",
        )

    course_id, is_published = row
    if not is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    return course_id


async def _get_lesson_course_id(lesson_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(Course.id, Course.is_published)
        .join(Section, Section.course_id == Course.id)
        .join(Lesson, Lesson.section_id == Section.id)
        .where(Lesson.id == lesson_id)
    )
    row = result.one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found",
        )

    course_id, is_published = row
    if not is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    return course_id


async def _ensure_published_course(course_id: int, db: AsyncSession) -> Course:
    course = await db.get(Course, course_id)
    if not course or not course.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return course


async def _ensure_user_enrolled(
    *,
    course_id: int,
    user_id: int,
    db: AsyncSession,
) -> None:
    result = await db.execute(
        select(Enrollment.id).where(
            and_(
                Enrollment.course_id == course_id,
                Enrollment.user_id == user_id,
            )
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enrollment not found",
        )


async def complete_step(
    *,
    step_id: int,
    user_id: int,
    db: AsyncSession,
) -> StepProgress:
    course_id = await _get_step_course_id(step_id=step_id, db=db)
    await _ensure_user_enrolled(course_id=course_id, user_id=user_id, db=db)

    result = await db.execute(
        select(StepProgress).where(
            and_(
                StepProgress.step_id == step_id,
                StepProgress.user_id == user_id,
            )
        )
    )
    progress = result.scalar_one_or_none()
    if progress is not None:
        return progress

    progress = StepProgress(
        step_id=step_id,
        user_id=user_id,
    )
    db.add(progress)

    try:
        await db.commit()
        await db.refresh(progress)
        return progress
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to complete step due to integrity error",
        )


async def uncomplete_step(
    *,
    step_id: int,
    user_id: int,
    db: AsyncSession,
) -> None:
    course_id = await _get_step_course_id(step_id=step_id, db=db)
    await _ensure_user_enrolled(course_id=course_id, user_id=user_id, db=db)

    result = await db.execute(
        select(StepProgress).where(
            and_(
                StepProgress.step_id == step_id,
                StepProgress.user_id == user_id,
            )
        )
    )
    progress = result.scalar_one_or_none()
    if progress is None:
        return

    try:
        await db.delete(progress)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to uncomplete step due to integrity error",
        )


async def is_step_completed(
    *,
    step_id: int,
    user_id: int,
    db: AsyncSession,
) -> bool:
    result = await db.execute(
        select(StepProgress.id).where(
            and_(
                StepProgress.step_id == step_id,
                StepProgress.user_id == user_id,
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def get_lesson_progress(
    *,
    lesson_id: int,
    user_id: int,
    db: AsyncSession,
) -> LessonProgress:
    course_id = await _get_lesson_course_id(lesson_id=lesson_id, db=db)
    await _ensure_user_enrolled(course_id=course_id, user_id=user_id, db=db)

    step_result = await db.execute(
        select(Step.id)
        .where(Step.lesson_id == lesson_id)
        .order_by(Step.order, Step.id)
    )
    step_ids = list(step_result.scalars().all())

    if not step_ids:
        return LessonProgress(
            lesson_id=lesson_id,
            completed_step_ids=[],
            completed_count=0,
            total_count=0,
            percent=0,
        )

    progress_result = await db.execute(
        select(StepProgress.step_id)
        .where(
            and_(
                StepProgress.user_id == user_id,
                StepProgress.step_id.in_(step_ids),
            )
        )
    )
    completed_set = set(progress_result.scalars().all())
    completed_step_ids = [
        step_id for step_id in step_ids if step_id in completed_set
    ]
    completed_count = len(completed_step_ids)
    total_count = len(step_ids)

    return LessonProgress(
        lesson_id=lesson_id,
        completed_step_ids=completed_step_ids,
        completed_count=completed_count,
        total_count=total_count,
        percent=round(completed_count / total_count * 100),
    )


async def get_course_sections_progress(
    *,
    course_id: int,
    user_id: int,
    db: AsyncSession,
) -> CourseSectionsProgress:
    await _ensure_published_course(course_id=course_id, db=db)
    await _ensure_user_enrolled(course_id=course_id, user_id=user_id, db=db)

    result = await db.execute(
        select(
            Section.id,
            Lesson.id,
            Step.id,
            StepProgress.id,
        )
        .outerjoin(Lesson, Lesson.section_id == Section.id)
        .outerjoin(Step, Step.lesson_id == Lesson.id)
        .outerjoin(
            StepProgress,
            and_(
                StepProgress.step_id == Step.id,
                StepProgress.user_id == user_id,
            ),
        )
        .where(Section.course_id == course_id)
        .order_by(Section.order, Section.id, Lesson.order, Lesson.id, Step.order, Step.id)
    )

    section_stats: dict[int, dict[str, object]] = {}
    for section_id, lesson_id, step_id, progress_id in result.all():
        stats = section_stats.setdefault(
            section_id,
            {
                "lesson_ids": set(),
                "lesson_steps": {},
                "completed_steps": 0,
                "total_steps": 0,
            },
        )

        lesson_ids = stats["lesson_ids"]
        lesson_steps = stats["lesson_steps"]

        if lesson_id is not None:
            lesson_ids.add(lesson_id)
            lesson_steps.setdefault(
                lesson_id,
                {"completed_steps": 0, "total_steps": 0},
            )

        if step_id is not None:
            stats["total_steps"] += 1
            lesson_step_stats = lesson_steps[lesson_id]
            lesson_step_stats["total_steps"] += 1

            if progress_id is not None:
                stats["completed_steps"] += 1
                lesson_step_stats["completed_steps"] += 1

    sections = []
    for section_id, stats in section_stats.items():
        lesson_steps = stats["lesson_steps"]
        total_step_count = stats["total_steps"]
        completed_step_count = stats["completed_steps"]
        completed_lesson_count = sum(
            1
            for lesson in lesson_steps.values()
            if lesson["total_steps"] > 0
            and lesson["completed_steps"] == lesson["total_steps"]
        )

        sections.append(
            SectionProgress(
                section_id=section_id,
                completed_step_count=completed_step_count,
                total_step_count=total_step_count,
                completed_lesson_count=completed_lesson_count,
                total_lesson_count=len(stats["lesson_ids"]),
                percent=round(completed_step_count / total_step_count * 100)
                if total_step_count
                else 0,
            )
        )

    return CourseSectionsProgress(course_id=course_id, sections=sections)
