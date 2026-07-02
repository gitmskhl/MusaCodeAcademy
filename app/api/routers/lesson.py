from fastapi import APIRouter, status
from app.schemas.section import SectionPublic, SectionAdmin, SectionUpdate, SectionOrderUpdateList
from app.schemas.lesson import (
    LessonAdmin,
    LessonCreate,
    LessonPublic,
    LessonUpdate, 
)
from app.services import section as service_section
from app.services import lesson as service_lesson
from app.api.dependencies import DBSession, OnlyAdmin

router = APIRouter()

@router.get('/{lesson_id}', response_model=LessonPublic)
async def get_lesson(lesson_id: int, db: DBSession):
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