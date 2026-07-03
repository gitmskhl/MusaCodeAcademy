from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Step, Lesson
from app.schemas.steps.step import StepCreate

async def create_step(lesson_id: int, stepInfo: StepCreate, db: AsyncSession) -> Step:
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lesson not found"
        )
    max_order = await db.scalar(
        select(func.max(Step.order))
            .where(Step.lesson_id == lesson_id)
    )
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
        await db.refresh(new_step)
        return new_step
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create step due to integrity error"
        )  
