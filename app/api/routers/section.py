from fastapi import APIRouter, status
from app.schemas.section import SectionPublic, SectionAdmin, SectionUpdate
from app.services import section as service_section
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