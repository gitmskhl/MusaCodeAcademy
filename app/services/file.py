from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException, status
from app.models import File
from app.services.storage import SavedFile

class FileService:
    
    async def create(
        self,
        db: AsyncSession,
        saved_file: SavedFile
    ) -> File:
        new_file = File(
            file_type=saved_file.file_type,
            original_filename=saved_file.original_filename,
            storage_path=saved_file.storage_path,
            mime_type=saved_file.mime_type,
            size=saved_file.size
        )

        db.add(new_file)
        try:        
            await db.commit()
            return new_file
        except Exception:
            await db.rollback()
            raise


    async def delete(
            self,
            db: AsyncSession,
            file_id: int
    ) -> str:
        file = await db.get(File, file_id)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        try:
            storage_path = file.storage_path
            await db.delete(file)
            await db.commit()
            return storage_path
        except Exception:
            await db.rollback()
            raise

    async def get_many(self, file_ids: list[int], db: AsyncSession) -> list[File]:
        result = await db.execute(
            select(File)
                .where(File.id.in_(set(file_ids)))
        )
        return result.scalars().all()


file_service = FileService()
