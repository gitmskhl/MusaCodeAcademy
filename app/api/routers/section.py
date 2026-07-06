from fastapi import APIRouter, status
from app.schemas.section import SectionPublic, SectionAdmin, SectionUpdate, SectionOrderUpdateList
from app.schemas.lesson import LessonAdmin, LessonCreate, LessonPublic
from app.services import section as service_section
from app.services import lesson as service_lesson
from app.api.dependencies import DBSession, OnlyAdmin

router = APIRouter()

@router.get('/{section_id}', response_model=SectionPublic)
async def get_section(section_id: int, db: DBSession):
    return await service_section.get_section(
        section_id=section_id,
        db=db,
        check_course=True
    )
    

@router.get('/{section_id}/admin', response_model=SectionAdmin)
async def get_section_admin(section_id: int, admin: OnlyAdmin, db: DBSession):
    return await service_section.get_section(
        section_id=section_id,
        db=db,
        check_course=False
    )
    

@router.delete('/{section_id}/admin', status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(section_id: int, admin: OnlyAdmin, db: DBSession):
    await service_section.delete_section(section_id=section_id, db=db)
    
    
@router.patch('/{section_id}/admin', response_model=SectionAdmin)
async def update_section(section_id: int, sectionUpdate: SectionUpdate, admin: OnlyAdmin, db: DBSession):
    return await service_section.update_section(section_id=section_id, sectionUpdate=sectionUpdate, db=db)


@router.patch('/admin/order', response_model=list[SectionAdmin])
async def update_orders(order_list: SectionOrderUpdateList, admin: OnlyAdmin, db: DBSession):
    return await service_section.update_section_orders(order_list=order_list, db=db)


# ------------------------------- /api/sections/{section_id}/admin/lessons -------------------------------

@router.post(
    '/{section_id}/admin/lessons',
    response_model=LessonAdmin,
    status_code=status.HTTP_201_CREATED
)
async def create_lesson(section_id: int, lessonCreate: LessonCreate, admin: OnlyAdmin, db: DBSession):
    return await service_lesson.create_lesson(
        section_id=section_id,
        lessonInfo=lessonCreate,
        db=db
    )


@router.get('/{section_id}/lessons', response_model=list[LessonPublic])
async def get_lessons(section_id: int, db: DBSession):
    return await service_lesson.get_lessons(section_id=section_id, db=db, check_course_published=True)


@router.get('{section_id}/lessons-list', response_model=)

@router.get('/{section_id}/admin/lessons', response_model=list[LessonAdmin])
async def get_lessons_admin(section_id: int, admin: OnlyAdmin, db: DBSession):
    return await service_lesson.get_lessons(section_id=section_id, db=db, check_course_published=False)