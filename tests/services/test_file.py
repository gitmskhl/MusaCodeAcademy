from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.enums import FileType
from app.models import File
from app.services.file import FileService
from app.services.storage import SavedFile


def make_saved_file(
    *,
    storage_path: str = "images/test.png",
) -> SavedFile:
    return SavedFile(
        original_filename="profile.png",
        storage_path=storage_path,
        mime_type="image/png",
        file_type=FileType.IMAGE,
        size=1024,
    )


@pytest.mark.asyncio
async def test_create_file_success(db):
    saved_file = make_saved_file()

    created_file = await FileService().create(
        db=db,
        saved_file=saved_file,
    )

    assert created_file.id is not None
    assert created_file.original_filename == saved_file.original_filename
    assert created_file.storage_path == saved_file.storage_path
    assert created_file.mime_type == saved_file.mime_type
    assert created_file.file_type == saved_file.file_type
    assert created_file.size == saved_file.size
    assert created_file.created_at is not None

    persisted_file = await db.get(File, created_file.id)
    assert persisted_file is created_file


@pytest.mark.asyncio
async def test_create_file_with_duplicate_storage_path_rolls_back(db):
    service = FileService()
    saved_file = make_saved_file()
    created_file = await service.create(db=db, saved_file=saved_file)

    with pytest.raises(IntegrityError):
        await service.create(db=db, saved_file=saved_file)

    result = await db.execute(
        select(File).where(File.storage_path == saved_file.storage_path)
    )
    files = result.scalars().all()

    assert [file.id for file in files] == [created_file.id]


@pytest.mark.asyncio
async def test_create_file_propagates_commit_error_and_rolls_back():
    error = RuntimeError("commit failed")
    db = Mock()
    db.commit = AsyncMock(side_effect=error)
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()

    with pytest.raises(RuntimeError, match="commit failed"):
        await FileService().create(
            db=db,
            saved_file=make_saved_file(),
        )

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_not_awaited()
    db.rollback.assert_awaited_once()
