import pytest
from app.enums import FileType

@pytest.mark.asyncio
async def test_save_valid_png_success(storage, valid_png):
    saved = await storage.save_image(valid_png)

    assert saved.original_filename == "valid.png"
    assert saved.mime_type == "image/png"
    assert saved.file_type == FileType.IMAGE
    assert saved.size > 0

    saved_path = storage.upload_dir / saved.storage_path
    assert saved_path.exists()
    assert saved_path.is_file()
    assert saved_path.stat().st_size() == saved.size