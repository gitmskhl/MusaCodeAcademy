from sqlalchemy.ext.asyncio import AsyncSession

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
            await db.refresh(new_file)
            return new_file
        except Exception:
            await db.rollback()
            raise

file_service = FileService()