from fastapi import APIRouter, status, UploadFile

from app.schemas.file import FilePublic
from app.api.dependencies import DBSession, OnlyAdmin
from app.services.storage import storage_service
from app.services.file import file_service

router = APIRouter()


@router.post('/images', response_model=FilePublic, status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile, admin: OnlyAdmin, db: DBSession):
    saved_file = await storage_service.save_image(file)

    try:
        db_file  = await file_service.create(saved_file=saved_file, db=db)
        return db_file 
    except Exception:
        await storage_service.delete(saved_file.storage_path)
        raise