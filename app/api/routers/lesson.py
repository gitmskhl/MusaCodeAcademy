from fastapi import APIRouter, status
from app.schemas.lesson import (
    LessonAdmin,
    LessonPublic,
    LessonUpdate,
    LessonOrderUpdateList
)
from app.schemas.steps.step import StepAdmin, StepCreate, StepPublic
from app.services import lesson as service_lesson
from app.services import step as service_step
from app.api.dependencies import CurrentUser, DBSession, OnlyAdmin

router = APIRouter()

@router.get('/{lesson_id}', response_model=LessonPublic)
async def get_lesson(lesson_id: int, _: CurrentUser, db: DBSession):
    return await service_lesson.get_lesson(lesson_id=lesson_id, db=db, check_course_published=True)


@router.get('/{lesson_id}/admin', response_model=LessonAdmin)
async def get_lesson_admin(lesson_id: int, admin: OnlyAdmin, db: DBSession):
    return await service_lesson.get_lesson(lesson_id=lesson_id, db=db, check_course_published=False)


@router.delete('/{lesson_id}/admin', status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(lesson_id: int, admin: OnlyAdmin, db: DBSession):
    await service_lesson.delete_lesson(lesson_id=lesson_id, db=db)
    

@router.patch('/{lesson_id}/admin', response_model=LessonAdmin)
async def update_lesson(lesson_id: int, lessonUpdate: LessonUpdate, admin: OnlyAdmin, db: DBSession):
    return await service_lesson.update_lesson(lesson_id=lesson_id, lessonUpdate=lessonUpdate, db=db)


@router.patch('/admin/order', response_model=list[LessonAdmin])
async def update_orders(order_list: LessonOrderUpdateList, admin: OnlyAdmin, db: DBSession):
    return await service_lesson.update_lesson_orders(order_list=order_list, db=db)


@router.post('/{lesson_id}/steps/admin', response_model=StepAdmin, status_code=status.HTTP_201_CREATED)
async def create_step(lesson_id: int, stepInfo: StepCreate, admin: OnlyAdmin, db: DBSession):
    return await service_step.create_step(lesson_id=lesson_id, stepInfo=stepInfo, db=db)


@router.get('/{lesson_id}/steps', response_model=list[StepPublic])
async def get_steps(lesson_id: int, _: CurrentUser, db: DBSession):
    return await service_step.get_steps(lesson_id=lesson_id, db=db, check_course_published=True)


@router.get('/{lesson_id}/steps/admin', response_model=list[StepAdmin])
async def get_steps_admin(lesson_id: int, admin: OnlyAdmin, db: DBSession):
    return await service_step.get_steps(lesson_id=lesson_id, db=db, check_course_published=False)
