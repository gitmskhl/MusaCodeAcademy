from typing import Annotated
from fastapi import APIRouter, status, UploadFile, Query

from app.schemas.file import FilePublic, FileReference
from app.api.dependencies import DBSession, OnlyAdmin, CurrentUser
from app.services.storage import storage_service
from app.services.file import file_service

router = APIRouter()

@router.get("", response_model=list[FileReference])
async def get_files(
    ids: Annotated[list[int], Query()],
    _: CurrentUser,
    db: DBSession
):
    files = await file_service.get_many(file_ids=ids, db=db)
    return [
        FileReference(
            id=file.id,
            url=storage_service.make_url(file.storage_path)
        )
        for file in files
    ]


@router.post('/images', response_model=FilePublic, status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile, _: OnlyAdmin, db: DBSession):
    saved_file = await storage_service.save_image(file)

    try:
        db_file  = await file_service.create(saved_file=saved_file, db=db)
        return db_file 
    except Exception:
        await storage_service.delete(saved_file.storage_path)
        raise


@router.delete('/{file_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(file_id: int, _: OnlyAdmin, db: DBSession):
    storage_path = await file_service.delete(file_id=file_id, db=db)
    await storage_service.delete(storage_path=storage_path)