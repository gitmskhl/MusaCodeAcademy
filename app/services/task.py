from fastapi import status, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.task import TaskCreate, TaskUpdate, LocalTaskTests
from app.models import Task, Step, TestCase
from app.enums import TaskCheckingMode


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
        checking_mode=taskInfo.checking_mode,
        starter_code=taskInfo.starter_code,
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


async def get_local_tests(task_id: int, db: AsyncSession) -> LocalTaskTests:
    task = await get_task(task_id=task_id, db=db)
    if task.checking_mode != TaskCheckingMode.LOCAL:
        raise HTTPException(status_code=409, detail="Task requires server checking")
    # Hidden tests are also required in the browser for local checking.
    tests = (await db.scalars(
        select(TestCase).where(TestCase.task_id == task_id)
        .order_by(TestCase.order, TestCase.id)
    )).all()
    if not tests:
        raise HTTPException(status_code=409, detail="Task has no tests")
    return LocalTaskTests(
        task_id=task.id, time_limit_ms=task.time_limit_ms, test_cases=tests
    )


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


async def update_task(task_id: int, taskUpdate: TaskUpdate, db: AsyncSession) -> Task:
    task = await get_task(task_id=task_id, db=db)
    step = await db.get(Step, task.step_id)
    if not step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    for key, val in taskUpdate.model_dump(exclude_unset=True).items():
        setattr(task, key, val)
    
    try:
        await db.commit()
        await db.refresh(task)
        return task
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task already exists for this step"
        )
