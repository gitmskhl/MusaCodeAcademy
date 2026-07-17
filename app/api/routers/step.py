from fastapi import APIRouter, status
from app.schemas.steps.step import StepPublic, StepAdmin, StepUpdate, StepOrderUpdateList, StepViewer
from app.schemas.task import TaskPublic
from app.services import activity as service_activity
from app.services import task as service_task
from app.services import step as service_step
from app.api.dependencies import DBSession, OnlyAdmin, StepEnrolledUser, StepViewerEnrolledUser

router = APIRouter()


@router.get('/{step_id}', response_model=StepPublic)
async def get_step(step_id: int, _: StepEnrolledUser, db: DBSession):
    return await service_step.get_step(step_id=step_id, db=db, check_course_published=True)


@router.get('/{step_id}/admin', response_model=StepAdmin)
async def get_step_admin(step_id: int, admin: OnlyAdmin, db: DBSession):
    return await service_step.get_step(step_id=step_id, db=db, check_course_published=False)


@router.get('/{step_id}/viewer', response_model=StepViewer)
async def get_step_viewer(
    course_slug: str,
    step_id: int,
    currentUser: StepViewerEnrolledUser,
    db: DBSession,
):
    viewer = await service_step.get_step_viewer(
        step_id=step_id,
        course_slug=course_slug,
        db=db,
    )
    await service_activity.record_course_visit(
        step_id=step_id,
        course_slug=course_slug,
        user_id=currentUser.id,
        db=db,
    )
    return viewer


@router.delete('/{step_id}/admin', status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(step_id: int, admin: OnlyAdmin, db: DBSession):
    await service_step.delete_step(step_id=step_id, db=db)
    

@router.patch('/{step_id}/admin', response_model=StepAdmin)
async def update_step(step_id: int, stepInfo: StepUpdate, admin: OnlyAdmin, db: DBSession):
    return await service_step.update_step(step_id=step_id, stepInfo=stepInfo, db=db)


@router.patch('/admin/order', response_model=list[StepAdmin])
async def update_steps_order(order_list: StepOrderUpdateList, admin: OnlyAdmin, db: DBSession):
    return await service_step.update_steps_order(order_list=order_list, db=db)


@router.get('/{step_id}/task', response_model=TaskPublic)
async def get_task_by_step_id(step_id: int, _: StepEnrolledUser, db: DBSession):
    return await service_task.get_task_by_step(
        step_id=step_id,
        db=db
    )
