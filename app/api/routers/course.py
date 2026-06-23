from fastapi import APIRouter, status, HTTPException
from app.models.course import Course
from app.schemas.course import CourseCreate, CoursePublic, CourseUpdate
from app.api.dependencies import OnlyAdmin, DBSession
from app.services.course import (
    create_course as service_create_coure,
    get_all_courses,
    update_course as service_update_course
)


router = APIRouter()

@router.get('', response_model=list[CoursePublic])
async def get_courses(db: DBSession):
    return await get_all_courses(db)


@router.post('', response_model=CoursePublic, status_code=status.HTTP_201_CREATED)
async def create_course(courseInfo: CourseCreate, admin: OnlyAdmin, db: DBSession):
    return await service_create_coure(courseInfo, db)


@router.patch('/{course_id}', response_model=CoursePublic)
async def update_course(
    course_id: int,
    updateInfo: CourseUpdate,
    admin: OnlyAdmin,
    db: DBSession
):
    return await service_update_course(course_id, updateInfo, db)