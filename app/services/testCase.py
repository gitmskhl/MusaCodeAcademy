from fastapi import status, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.testCase import TestCaseCreate, TestCaseUpdate
from app.models import TestCase, Task

async def create_test_case(testInfo: TestCaseCreate, db: AsyncSession) -> TestCase:
    task = await db.get(Task, testInfo.task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    last_order = (await db.execute(
        select(func.max(TestCase.order))
            .where(TestCase.task_id == testInfo.task_id)
    )).scalar()

    order = 1 if last_order is None else last_order + 1

    new_test_case = TestCase(
        task_id = testInfo.task_id,
        input = testInfo.input,
        expected_output = testInfo.expected_output,
        is_hidden = testInfo.is_hidden,
        order = order
    )

    db.add(new_test_case)

    try:
        await db.commit()
        await db.refresh(new_test_case)
        return new_test_case
    except Exception:
        await db.rollback()
        raise


async def get_test_cases_by_task(task_id: int, db: AsyncSession) -> list[TestCase]:
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    result = await db.execute(
        select(TestCase)
            .where(TestCase.task_id == task_id)
            .order_by(TestCase.order)
    )
    
    return result.scalars().all() 


async def update_test_case(test_case_id: int, test_case_update: TestCaseUpdate, db: AsyncSession) -> TestCase:
    test_case = await db.get(TestCase, test_case_id)
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test Case not found"
        )
    
    data = test_case_update.model_dump(exclude_unset=True)
    if not data:
        return test_case
    for key, val in data.items():
        setattr(test_case, key, val)
    
    try:
        await db.commit()
        await db.refresh(test_case)
        return test_case
    except Exception:
        await db.rollback()
        raise


async def delete_test_case(test_case_id: int, db: AsyncSession):
    test_case = await db.get(TestCase, test_case_id)
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test Case not found"
        )
    
    try:
        await db.delete(test_case)
        await db.commit()
    except Exception:
        await db.rollback()
        raise