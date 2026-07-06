from fastapi import APIRouter, status, HTTPException
from app.models.course import Course
from app.schemas.course import CourseCreate, CoursePublic, CourseUpdate, CourseAdmin
from app.schemas.section import SectionPublic, SectionAdmin, SectionCreate
from app.api.dependencies import OnlyAdmin, DBSession
from app.services import course as service_course
from app.services import section as service_section


router = APIRouter()

# ---------------------------------- /api/courses/.../admin --------------------------------------

# GET /api/courses/admin
@router.get('/admin', response_model=list[CourseAdmin])
async def get_courses_private(admin: OnlyAdmin, db: DBSession):
    return await service_course.get_all_courses(db)


# GET /api/courses/{id}/admin
@router.get('/{course_id}/admin', response_model=CourseAdmin)
async def get_course_private_info(course_id: int, admin: OnlyAdmin, db: DBSession):
    return await service_course.get_course_info(course_id, db)


# ---------------------------------- /api/courses -----------------------------------------
# GET /api/courses
@router.get('', response_model=list[CoursePublic])
async def get_courses(db: DBSession):
    return await service_course.get_published_courses(db)


# POST /api/courses
@router.post('', response_model=CoursePublic, status_code=status.HTTP_201_CREATED)
async def create_course(courseInfo: CourseCreate, admin: OnlyAdmin, db: DBSession):
    return await service_course.create_course(courseInfo, db)

# ---------------------------------- /api/courses/{id} -----------------------------------------

# GET /api/courses/{id} 
@router.get('/{course_id}', response_model=CoursePublic)
async def get_course_info(course_id: int, db: DBSession):
    return await service_course.get_published_course_info(course_id, db)


# PATCH /api/courses/{id}
@router.patch('/{course_id}', response_model=CoursePublic)
async def update_course(
    course_id: int,
    updateInfo: CourseUpdate,
    admin: OnlyAdmin,
    db: DBSession
):
    return await service_course.update_course(course_id, updateInfo, db)


# DELETE /api/courses{id}
@router.delete('/{course_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: int,
    admin: OnlyAdmin,
    db: DBSession
):
    await service_course.delete_course(course_id, db)
    

# ---------------------------------- /api/courses/{id}/sections --------------------------------

@router.get('/{course_id}/sections', response_model=list[SectionPublic])
async def get_course_sections(course_id: int, db: DBSession):
    return await service_section.get_course_sections(course_id=course_id, db=db, check_published=True)
    

@router.post('/{course_id}/sections', response_model=SectionPublic, status_code=status.HTTP_201_CREATED)
async def create_course_section(
    course_id: int,
    sectionInfo: SectionCreate,
    admin: OnlyAdmin,
    db: DBSession
):
    return await service_section.create_course_section(
        course_id=course_id,
        sectionInfo=sectionInfo,
        db=db
    )



# ----------------------------- /api/courses/{id}/sections/admin --------------------------------
@router.get('/{course_id}/sections/admin', response_model=list[SectionAdmin])
async def get_course_sections_admin(course_id: int, admin: OnlyAdmin, db: DBSession):
    return await service_section.get_course_sections(course_id=course_id, db=db, check_published=False)
