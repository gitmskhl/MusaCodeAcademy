from pydantic import BaseModel, Field, ConfigDict

from app.enums import FileType

class FilePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_type: FileType
    original_filename: str
    storage_path: str
    mime_type: str
    size: int


class FileUploadResponse(BaseModel):
    id: int
    url: str