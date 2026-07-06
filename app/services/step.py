from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from app.models import Step, Lesson, Course, Section
from app.schemas.steps.step import (
    StepCreate,
    StepNavigation,
    StepUpdate,
    StepOrderUpdateList,
    StepViewer,
    StepViewerLesson,
    StepSummary,
    StepPublic,
)

async def create_step(lesson_id: int, stepInfo: StepCreate, db: AsyncSession) -> Step:
    parent_and_order = (
        await db.execute(
            select(Lesson.id, func.max(Step.order))
            .outerjoin(Step, Step.lesson_id == Lesson.id)
            .where(Lesson.id == lesson_id)
            .group_by(Lesson.id)
        )
    ).one_or_none()
    if parent_and_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson not found"
        )
    _, max_order = parent_and_order
    order = 0 if max_order is None else max_order + 1
    new_step = Step(
        lesson_id=lesson_id,
        title=stepInfo.title,
        order=order,
        content=stepInfo.content.model_dump()
    )
    db.add(new_step)
    
    try:
        await db.commit()
        return new_step
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create step due to integrity error"
        )  


async def get_steps(lesson_id: int, db: AsyncSession, check_course_published: bool = True) -> list[Step]:
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
            detail=f"Lesson not found"
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
    result = await db.execute(
        select(Step)
            .where(Step.lesson_id == lesson_id)
            .order_by(Step.order)
    )
    steps = result.scalars().all()
    return steps # type: ignore


async def get_step(step_id: int, db: AsyncSession, check_course_published: bool = True) -> Step:
    if check_course_published:
        row = (
            await db.execute(
                select(
                    Step,
                    Lesson.id,
                    Section.id,
                    Course.is_published,
                )
                .outerjoin(Lesson, Lesson.id == Step.lesson_id)
                .outerjoin(Section, Section.id == Lesson.section_id)
                .outerjoin(Course, Course.id == Section.course_id)
                .where(Step.id == step_id)
            )
        ).one_or_none()
        step, lesson_id, section_id, course_is_published = (
            row if row else (None, None, None, None)
        )
    else:
        step = await db.get(Step, step_id)
        lesson_id = section_id = course_is_published = None

    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step not found"
        )
    if check_course_published:
        if lesson_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lesson not found"
            )
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
    return step
    


async def delete_step(step_id: int, db: AsyncSession):
    step = await db.get(Step, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step not found"
        )
    try:
        await db.delete(step)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete step due to integrity error"
        )
        
        
async def update_step(step_id: int, stepInfo: StepUpdate, db: AsyncSession) -> Step:
    step = await db.get(Step, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step not found"
        )
    for key, value in stepInfo.model_dump(exclude_unset=True).items():
        setattr(step, key, value)
    
    try:
        await db.commit()
        return step
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update step"
        )
        
        
async def update_steps_order(order_list: StepOrderUpdateList, db: AsyncSession) -> list[Step]:
    steps_ids = [item.id for item in order_list.steps]
    if len(steps_ids) != len(set(steps_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate step IDs found"
        )
    # check for duplicate order values
    order_values = [item.order for item in order_list.steps]
    if len(order_values) != len(set(order_values)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate order values found"
        )
    steps = await db.execute(
        select(Step)
            .where(Step.id.in_(steps_ids))
    )
    scalar_steps = steps.scalars().all()
    section_ids = {step.lesson_id for step in scalar_steps}
    if len(section_ids) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All steps must belong to the same lesson"
        )
    new_orders = {item.id: item.order for item in order_list.steps}
    for step in scalar_steps:
        step.order = new_orders[step.id]
    try:
        await db.commit()
        return scalar_steps # type: ignore
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update step orders due to integrity error"
        )


async def get_step_viewer(
    step_id: int,
    course_slug: str,
    db: AsyncSession,
) -> StepViewer:
    selected_step = aliased(Step)
    lesson_step = aliased(Step)
    result = await db.execute(
        select(
            selected_step,
            Lesson.id,
            Lesson.section_id,
            Lesson.title,
            lesson_step.id,
            lesson_step.title,
        )
        .join(Lesson, selected_step.lesson_id == Lesson.id)
        .join(Section, Lesson.section_id == Section.id)
        .join(Course, Section.course_id == Course.id)
        .join(lesson_step, lesson_step.lesson_id == Lesson.id)
        .where(
            selected_step.id == step_id,
            Course.slug == course_slug,
            Course.is_published.is_(True),
        )
        .order_by(lesson_step.order, lesson_step.id)
    )
    rows = result.all()

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found",
        )

    step, lesson_id, section_id, lesson_title, _, _ = rows[0]
    lesson_steps = [
        StepSummary(id=lesson_step_id, title=lesson_step_title)
        for _, _, _, _, lesson_step_id, lesson_step_title in rows
    ]
    step_ids = [lesson_step.id for lesson_step in lesson_steps]

    try:
        index = step_ids.index(step.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found",
        )

    previous_step_id = step_ids[index - 1] if index > 0 else None
    next_step_id = (
        step_ids[index + 1]
        if index + 1 < len(step_ids)
        else None
    )

    return StepViewer(
        step=StepPublic.model_validate(step),
        navigation=StepNavigation(
            position=index + 1,
            total=len(step_ids),
            previous_step_id=previous_step_id,
            next_step_id=next_step_id,
        ),
        lesson=StepViewerLesson(
            id=lesson_id,
            section_id=section_id,
            title=lesson_title,
            steps=lesson_steps,
        ),
    )


async def get_first_lesson_step_id(
    lesson_id: int,
    course_slug: str,
    db: AsyncSession,
) -> int:
    result = await db.execute(
        select(Step.id)
        .join(Lesson, Step.lesson_id == Lesson.id)
        .join(Section, Lesson.section_id == Section.id)
        .join(Course, Section.course_id == Course.id)
        .where(
            Lesson.id == lesson_id,
            Course.slug == course_slug,
            Course.is_published.is_(True),
        )
        .order_by(Step.order, Step.id)
        .limit(1)
    )
    step_id = result.scalar_one_or_none()

    if step_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson step not found",
        )

    return step_id
