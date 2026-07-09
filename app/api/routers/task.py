from fastapi import APIRouter, status
from app.schemas.task import TaskPublic, TaskCreate, TaskUpdate
from app.api.dependencies import OnlyAdmin, DBSession
from app.services import task as service_task

router = APIRouter()


@router.post('/admin', response_model=TaskPublic, status_code=status.HTTP_201_CREATED)
async def create_task(taskInfo: TaskCreate, _: OnlyAdmin, db: DBSession):
    new_task = await service_task.create_task(
        taskInfo=taskInfo,
        db=db
    )
    return new_task


@router.get('/admin/{task_id}', response_model=TaskPublic)
async def get_task_admin(task_id: int, _: OnlyAdmin, db: DBSession):
    return await service_task.get_task(task_id=task_id, db=db)


@router.get('/admin/by-step/{step_id}', response_model=TaskPublic)
async def get_task_by_step_admin(step_id: int, _: OnlyAdmin, db: DBSession):
    return await service_task.get_task_by_step(step_id=step_id, db=db)


@router.delete('/admin/{task_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, _: OnlyAdmin, db: DBSession):
    await service_task.delete_task(task_id=task_id, db=db)


@router.patch('/admin/{task_id}', response_model=TaskPublic)
async def update_task(
    task_id: int,
    taskUpdate: TaskUpdate,
    _: OnlyAdmin,
    db: DBSession,
):
    return await service_task.update_task(
        task_id=task_id,
        taskUpdate=taskUpdate,
        db=db
    )
