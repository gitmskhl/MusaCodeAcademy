from fastapi import APIRouter, status
from app.schemas.testCase import TestCaseCreate, TestCasePublic, TestCaseUpdate
from app.api.dependencies import OnlyAdmin, DBSession, CurrentUser
from app.services import testCase as service_test_case


router = APIRouter()

@router.post('', response_model=TestCasePublic, status_code=status.HTTP_201_CREATED)
async def create_test_case(testInfo: TestCaseCreate, _: OnlyAdmin, db: DBSession):
    return await service_test_case.create_test_case(testInfo=testInfo, db=db)


@router.get('/{test_case_id}', response_model=TestCasePublic)
async def get_test_case(test_case_id: int, _: CurrentUser, db: DBSession):
    return await service_test_case.get_test_case(
        test_case_id=test_case_id,
        db=db
    )


@router.get('/admin/by-task/{task_id}', response_model=list[TestCasePublic])
async def get_test_cases(task_id: int, _: OnlyAdmin, db: DBSession):
    return await service_test_case.get_test_cases_by_task(
        task_id=task_id,
        db=db
    )


@router.patch('/admin/{test_case_id}', response_model=TestCasePublic)
async def update_test_case(test_case_id: int, test_case_update: TestCaseUpdate, _: OnlyAdmin, db: DBSession):
    return await service_test_case.update_test_case(
        test_case_id=test_case_id,
        test_case_update=test_case_update,
        db=db
    )


@router.delete('/admin/{test_case_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_test_case(test_case_id: int, _: OnlyAdmin, db: DBSession):
    return await service_test_case.delete_test_case(
        test_case_id=test_case_id,
        db=db
    )
