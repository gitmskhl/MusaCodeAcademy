from fastapi import status, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.task import TaskCreate
from app.models import Task, Step


async def create_task(taskInfo: TaskCreate, db: AsyncSession) -> Task:
    step = await db.get(Step, taskInfo.step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    
    task = (await db.execute(
        select(Task)
            .where(Task.step_id == taskInfo.step_id)
    )).scalar_one_or_none()
    if task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task already exists for this step"
        )

    new_task = Task(
        step_id=taskInfo.step_id,
        title=taskInfo.title,
        description=taskInfo.description,
        time_limit_ms=taskInfo.time_limit_ms,
        memory_limit_mb=taskInfo.memory_limit_mb
    )

    db.add(new_task)
    try:
        await db.commit()
        await db.refresh(new_task)
        return new_task
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task already exists for this step"
        )


async def get_task(task_id: int, db: AsyncSession) -> Task:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


async def get_task_by_step(step_id: int, db: AsyncSession) -> Task:
    step = await db.get(Step, step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )

    task = (await db.execute(
        select(Task)
            .where(Task.step_id == step_id)
    )).scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return task


async def delete_task(task_id: int, db: AsyncSession) -> None:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    try:
        await db.delete(task)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete task due to integrity error"
        )
