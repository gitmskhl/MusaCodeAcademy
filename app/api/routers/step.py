from fastapi import APIRouter, status
from app.schemas.steps.step import StepPublic, StepAdmin, StepUpdate
from app.services import step as service_step
from app.api.dependencies import DBSession, OnlyAdmin

router = APIRouter()


@router.get('/{step_id}', response_model=StepPublic)
async def get_step(step_id: int, db: DBSession):
    return await service_step.get_step(step_id=step_id, db=db, check_course_published=True)


@router.get('/{step_id}/admin', response_model=StepAdmin)
async def get_step_admin(step_id: int, admin: OnlyAdmin, db: DBSession):
    return await service_step.get_step(step_id=step_id, db=db, check_course_published=False)


@router.delete('/{step_id}/admin', status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(step_id: int, admin: OnlyAdmin, db: DBSession):
    await service_step.delete_step(step_id=step_id, db=db)
    

@router.patch('/{step_id}/admin', response_model=StepAdmin)
async def update_step(step_id: int, stepInfo: StepUpdate, admin: OnlyAdmin, db: DBSession):
    return await service_step.update_step(step_id=step_id, stepInfo=stepInfo, db=db)