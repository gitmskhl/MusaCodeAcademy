import aiofiles
import asyncio
from pathlib import Path
from dataclasses import dataclass
from fastapi import UploadFile
from uuid import uuid4
from PIL import Image, UnidentifiedImageError

from app.enums import FileType
from app.core.exceptions import (
    InvalidFileExtensionError,
    InvalidMimeTypeError,
    EmptyFilenameError,
    FileTooLargeError,
    EmptyFileError,
    InvalidImageContentError
)

UPLOAD_DIR = Path('uploads')
IMAGE_UPLOAD_DIR = UPLOAD_DIR / "images"

CHUNK_SIZE = 1024 * 1024 # 1 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024 # 10 MB

ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif"
}

@dataclass(slots=True)
class SavedFile:
    original_filename: str
    storage_path: str
    mime_type: str
    file_type: FileType
    size: int
    

class StorageService:
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self.image_upload_dir = upload_dir / "images"
        self.image_upload_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_image(path: Path, extension: str) -> None:
        expected_formats = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".webp": "WEBP",
            ".gif": "GIF",
        }
        try:
            with Image.open(path) as image:
                image.verify()

                if image.format != expected_formats[extension]:
                    raise InvalidImageContentError()
        except (UnidentifiedImageError, OSError, SyntaxError):
            raise InvalidImageContentError()

    @staticmethod
    async def _save_file(file: UploadFile, destPath: Path, max_file_size: int) -> int:
        total = 0
        try:
            async with aiofiles.open(destPath, "wb") as destStream:
                while chunk := await file.read(CHUNK_SIZE):
                    total += len(chunk)
                    if total > max_file_size:
                        raise FileTooLargeError()
                    
                    await destStream.write(chunk)
            if total == 0:
                raise EmptyFileError()
            
            return total
        except Exception:
            await asyncio.to_thread(destPath.unlink, missing_ok=True)
            raise
        finally:
            await file.close()

    
    @staticmethod
    async def _save_image_file(file: UploadFile, destPath: Path) -> int:
        real_image_size = await StorageService._save_file(file=file, destPath=destPath, max_file_size=MAX_IMAGE_SIZE)
        try:
            await asyncio.to_thread(
                StorageService._validate_image,
                destPath,
                destPath.suffix.lower()
            )
            return real_image_size
        except Exception:
            await asyncio.to_thread(destPath.unlink, missing_ok=True)
            raise
 
    async def save_image(self, file: UploadFile) -> SavedFile:
        if not file.filename:
            raise EmptyFilenameError()
        
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise InvalidFileExtensionError()
        
        mime_type = file.content_type
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise InvalidMimeTypeError()
        
        filename = f"{uuid4().hex}{ext}"
        real_image_size = await StorageService._save_image_file(file, self.image_upload_dir / filename)
        
        return SavedFile(
            original_filename=file.filename,
            storage_path=f"images/{filename}",
            mime_type=mime_type,
            file_type=FileType.IMAGE,
            size=real_image_size
        )


    async def delete(self, storage_path: str) -> None:
        path = self.upload_dir / storage_path
        await asyncio.to_thread(path.unlink, missing_ok=True)
        

storage_service = StorageService(upload_dir=UPLOAD_DIR)