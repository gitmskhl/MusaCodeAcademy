from fastapi import APIRouter, status, HTTPException
from app.models.course import Course
from app.schemas.course import CourseCreate, CoursePublic, CourseUpdate, CoursePrivate
from app.api.dependencies import OnlyAdmin, DBSession
from app.services.course import (
    create_course as service_create_coure,
    get_all_courses,
    get_published_courses,
    get_course_info,
    get_published_course_info,
    update_course as service_update_course,
    delete_course as service_delete_course
)


router = APIRouter()

@router.get('', response_model=list[CoursePublic])
async def get_courses(db: DBSession):
    return await get_published_courses(db)


@router.get('/admin', response_model=list[CoursePrivate])
async def get_courses_private(admin: OnlyAdmin, db: DBSession):
    return await get_all_courses(db)


@router.get('/{course_id}', response_model=CoursePublic)
async def get_course_info(course_id: int, db: DBSession):
    return await get_published_course_info(course_id, db)


@router.get('/{course_id}/admin', response_model=CoursePrivate)
async def get_course_private_info(course_id: int, admin: OnlyAdmin, db: DBSession):
    return await get_course_info(course_id, db)


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


@router.delete('/{course_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    admin: OnlyAdmin,
    db: DBSession
):
    await service_delete_course(course_id, db)