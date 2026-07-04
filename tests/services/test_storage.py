from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from starlette.datastructures import Headers

from app.core.exceptions import (
    EmptyFileError,
    EmptyFilenameError,
    FileTooLargeError,
    InvalidFileExtensionError,
    InvalidImageContentError,
    InvalidMimeTypeError,
)
from app.enums import FileType
from app.services import storage as storage_module


ASSETS_DIR = Path(__file__).parents[1] / "assets"


def make_upload_file(
    asset_name: str,
    *,
    filename: str | None = None,
    content_type: str = "image/png",
) -> UploadFile:
    return UploadFile(
        filename=filename if filename is not None else asset_name,
        file=BytesIO((ASSETS_DIR / asset_name).read_bytes()),
        headers=Headers({"content-type": content_type}),
    )


def assert_upload_dir_is_empty(storage) -> None:
    assert list(storage.image_upload_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_save_valid_png_success(storage, valid_png):
    saved = await storage.save_image(valid_png)

    assert saved.original_filename == "valid.png"
    assert saved.mime_type == "image/png"
    assert saved.file_type == FileType.IMAGE
    assert saved.size == (ASSETS_DIR / "valid.png").stat().st_size

    saved_path = storage.upload_dir / saved.storage_path
    assert saved.storage_path.startswith("images/")
    assert saved_path.suffix == ".png"
    assert saved_path.exists()
    assert saved_path.is_file()
    assert saved_path.stat().st_size == saved.size
    assert valid_png.file.closed


@pytest.mark.asyncio
async def test_save_valid_jpeg_success(storage):
    upload = make_upload_file(
        "valid.jpg",
        filename="PHOTO.JPEG",
        content_type="image/jpeg",
    )

    saved = await storage.save_image(upload)

    assert saved.original_filename == "PHOTO.JPEG"
    assert saved.mime_type == "image/jpeg"
    assert saved.file_type == FileType.IMAGE
    assert saved.size == (ASSETS_DIR / "valid.jpg").stat().st_size
    assert Path(saved.storage_path).suffix == ".jpeg"
    assert (storage.upload_dir / saved.storage_path).is_file()
    assert upload.file.closed


@pytest.mark.asyncio
async def test_save_image_without_filename_fails(storage):
    upload = make_upload_file("valid.png", filename="")

    with pytest.raises(EmptyFilenameError):
        await storage.save_image(upload)

    assert_upload_dir_is_empty(storage)


@pytest.mark.asyncio
async def test_save_text_file_fails_for_invalid_extension(storage):
    upload = make_upload_file("text.txt", content_type="text/plain")

    with pytest.raises(InvalidFileExtensionError):
        await storage.save_image(upload)

    assert_upload_dir_is_empty(storage)


@pytest.mark.asyncio
async def test_save_image_with_invalid_mime_type_fails(storage):
    upload = make_upload_file("valid.png", content_type="text/plain")

    with pytest.raises(InvalidMimeTypeError):
        await storage.save_image(upload)

    assert_upload_dir_is_empty(storage)


@pytest.mark.asyncio
async def test_save_empty_image_fails_and_removes_file(storage):
    upload = UploadFile(
        filename="empty.png",
        file=BytesIO(),
        headers=Headers({"content-type": "image/png"}),
    )

    with pytest.raises(EmptyFileError):
        await storage.save_image(upload)

    assert upload.file.closed
    assert_upload_dir_is_empty(storage)


@pytest.mark.asyncio
async def test_save_invalid_image_content_fails_and_removes_file(storage):
    upload = make_upload_file("invalid.png")

    with pytest.raises(InvalidImageContentError):
        await storage.save_image(upload)

    assert upload.file.closed
    assert_upload_dir_is_empty(storage)


@pytest.mark.asyncio
async def test_save_image_with_content_not_matching_extension_fails(storage):
    upload = make_upload_file(
        "valid.jpg",
        filename="valid.png",
        content_type="image/png",
    )

    with pytest.raises(InvalidImageContentError):
        await storage.save_image(upload)

    assert upload.file.closed
    assert_upload_dir_is_empty(storage)


@pytest.mark.asyncio
async def test_save_image_larger_than_limit_fails_and_removes_file(
    storage,
    monkeypatch,
):
    monkeypatch.setattr(storage_module, "MAX_IMAGE_SIZE", 1)
    upload = make_upload_file("valid.png")

    with pytest.raises(FileTooLargeError):
        await storage.save_image(upload)

    assert upload.file.closed
    assert_upload_dir_is_empty(storage)


@pytest.mark.asyncio
async def test_delete_saved_image(storage, valid_png):
    saved = await storage.save_image(valid_png)
    saved_path = storage.upload_dir / saved.storage_path

    await storage.delete(saved.storage_path)

    assert not saved_path.exists()


@pytest.mark.asyncio
async def test_delete_missing_image_does_not_fail(storage):
    await storage.delete("images/missing.png")

    assert_upload_dir_is_empty(storage)
