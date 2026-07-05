from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import status

from app.enums import FileType
from app.services.storage import SavedFile
from app.api.routers import file as file_router


FILE_FIELDS = {
    "id",
    "file_type",
    "original_filename",
    "storage_path",
    "mime_type",
    "size",
}


def make_saved_file() -> SavedFile:
    return SavedFile(
        original_filename="profile.png",
        storage_path="images/generated.png",
        mime_type="image/png",
        file_type=FileType.IMAGE,
        size=128,
    )


def make_db_file(saved_file: SavedFile, *, file_id: int = 1):
    return SimpleNamespace(
        id=file_id,
        file_type=saved_file.file_type,
        original_filename=saved_file.original_filename,
        storage_path=saved_file.storage_path,
        mime_type=saved_file.mime_type,
        size=saved_file.size,
    )


# GET /api/files


@pytest.mark.asyncio
async def test_get_files_success_for_authenticated_user(
    client,
    auth_headers,
    monkeypatch,
):
    first = make_db_file(make_saved_file(), file_id=1)
    second_saved_file = make_saved_file()
    second_saved_file.storage_path = "images/second.png"
    second = make_db_file(second_saved_file, file_id=2)
    get_many = AsyncMock(return_value=[first, second])
    monkeypatch.setattr(file_router.file_service, "get_many", get_many)

    response = await client.get(
        "/api/files",
        headers=auth_headers,
        params=[("ids", "1"), ("ids", "2")],
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {"id": 1, "url": "/uploads/images/generated.png"},
        {"id": 2, "url": "/uploads/images/second.png"},
    ]
    get_many.assert_awaited_once()
    assert get_many.await_args.kwargs["file_ids"] == [1, 2]
    assert get_many.await_args.kwargs["db"] is not None


@pytest.mark.asyncio
async def test_get_files_returns_only_files_found_by_service(
    client,
    auth_headers,
    monkeypatch,
):
    existing = make_db_file(make_saved_file(), file_id=1)
    get_many = AsyncMock(return_value=[existing])
    monkeypatch.setattr(file_router.file_service, "get_many", get_many)

    response = await client.get(
        "/api/files",
        headers=auth_headers,
        params=[("ids", "1"), ("ids", "999999")],
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {"id": 1, "url": "/uploads/images/generated.png"},
    ]
    assert get_many.await_args.kwargs["file_ids"] == [1, 999999]


@pytest.mark.asyncio
async def test_get_files_requires_ids(client, auth_headers, monkeypatch):
    get_many = AsyncMock()
    monkeypatch.setattr(file_router.file_service, "get_many", get_many)

    response = await client.get("/api/files", headers=auth_headers)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["query", "ids"]
    get_many.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_files_requires_authentication(client, monkeypatch):
    get_many = AsyncMock()
    monkeypatch.setattr(file_router.file_service, "get_many", get_many)

    response = await client.get("/api/files", params={"ids": "1"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
    get_many.assert_not_awaited()


# POST /api/files/images


@pytest.mark.asyncio
async def test_upload_image_success(
    client,
    admin_headers,
    monkeypatch,
):
    saved_file = make_saved_file()
    db_file = make_db_file(saved_file)
    save_image = AsyncMock(return_value=saved_file)
    create_file = AsyncMock(return_value=db_file)
    delete_from_storage = AsyncMock()
    monkeypatch.setattr(file_router.storage_service, "save_image", save_image)
    monkeypatch.setattr(file_router.file_service, "create", create_file)
    monkeypatch.setattr(
        file_router.storage_service,
        "delete",
        delete_from_storage,
    )

    response = await client.post(
        "/api/files/images",
        headers=admin_headers,
        files={"file": ("profile.png", b"image bytes", "image/png")},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert set(data) == FILE_FIELDS
    assert data == {
        "id": db_file.id,
        "file_type": "image",
        "original_filename": saved_file.original_filename,
        "storage_path": saved_file.storage_path,
        "mime_type": saved_file.mime_type,
        "size": saved_file.size,
    }
    save_image.assert_awaited_once()
    uploaded_file = save_image.await_args.args[0]
    assert uploaded_file.filename == "profile.png"
    assert uploaded_file.content_type == "image/png"
    create_file.assert_awaited_once()
    assert create_file.await_args.kwargs["saved_file"] is saved_file
    assert create_file.await_args.kwargs["db"] is not None
    delete_from_storage.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_image_removes_saved_file_when_database_create_fails(
    client,
    admin_headers,
    monkeypatch,
):
    saved_file = make_saved_file()
    save_image = AsyncMock(return_value=saved_file)
    create_file = AsyncMock(side_effect=RuntimeError("database failed"))
    delete_from_storage = AsyncMock()
    monkeypatch.setattr(file_router.storage_service, "save_image", save_image)
    monkeypatch.setattr(file_router.file_service, "create", create_file)
    monkeypatch.setattr(
        file_router.storage_service,
        "delete",
        delete_from_storage,
    )

    with pytest.raises(RuntimeError, match="database failed"):
        await client.post(
            "/api/files/images",
            headers=admin_headers,
            files={"file": ("profile.png", b"image bytes", "image/png")},
        )

    save_image.assert_awaited_once()
    create_file.assert_awaited_once()
    delete_from_storage.assert_awaited_once_with(saved_file.storage_path)


@pytest.mark.asyncio
async def test_upload_image_does_not_create_db_record_when_storage_fails(
    client,
    admin_headers,
    monkeypatch,
):
    save_image = AsyncMock(side_effect=RuntimeError("storage failed"))
    create_file = AsyncMock()
    delete_from_storage = AsyncMock()
    monkeypatch.setattr(file_router.storage_service, "save_image", save_image)
    monkeypatch.setattr(file_router.file_service, "create", create_file)
    monkeypatch.setattr(
        file_router.storage_service,
        "delete",
        delete_from_storage,
    )

    with pytest.raises(RuntimeError, match="storage failed"):
        await client.post(
            "/api/files/images",
            headers=admin_headers,
            files={"file": ("profile.png", b"image bytes", "image/png")},
        )

    create_file.assert_not_awaited()
    delete_from_storage.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_image_rejects_non_admin(
    client,
    auth_headers,
    monkeypatch,
):
    save_image = AsyncMock()
    monkeypatch.setattr(file_router.storage_service, "save_image", save_image)

    response = await client.post(
        "/api/files/images",
        headers=auth_headers,
        files={"file": ("profile.png", b"image bytes", "image/png")},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }
    save_image.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_image_requires_authentication(client, monkeypatch):
    save_image = AsyncMock()
    monkeypatch.setattr(file_router.storage_service, "save_image", save_image)

    response = await client.post(
        "/api/files/images",
        files={"file": ("profile.png", b"image bytes", "image/png")},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
    save_image.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_image_requires_file(client, admin_headers, monkeypatch):
    save_image = AsyncMock()
    monkeypatch.setattr(file_router.storage_service, "save_image", save_image)

    response = await client.post(
        "/api/files/images",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["body", "file"]
    save_image.assert_not_awaited()


# DELETE /api/files/{file_id}


@pytest.mark.asyncio
async def test_delete_image_success(
    client,
    admin_headers,
    monkeypatch,
):
    delete_file = AsyncMock(return_value="images/generated.png")
    delete_from_storage = AsyncMock()
    monkeypatch.setattr(file_router.file_service, "delete", delete_file)
    monkeypatch.setattr(
        file_router.storage_service,
        "delete",
        delete_from_storage,
    )

    response = await client.delete(
        "/api/files/42",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    delete_file.assert_awaited_once()
    assert delete_file.await_args.kwargs["file_id"] == 42
    assert delete_file.await_args.kwargs["db"] is not None
    delete_from_storage.assert_awaited_once_with(
        storage_path="images/generated.png"
    )


@pytest.mark.asyncio
async def test_delete_image_not_found_does_not_touch_storage(
    client,
    admin_headers,
    monkeypatch,
):
    delete_from_storage = AsyncMock()
    monkeypatch.setattr(
        file_router.storage_service,
        "delete",
        delete_from_storage,
    )

    response = await client.delete(
        "/api/files/999999",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "File not found"}
    delete_from_storage.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_image_does_not_touch_storage_when_db_delete_fails(
    client,
    admin_headers,
    monkeypatch,
):
    delete_file = AsyncMock(side_effect=RuntimeError("database failed"))
    delete_from_storage = AsyncMock()
    monkeypatch.setattr(file_router.file_service, "delete", delete_file)
    monkeypatch.setattr(
        file_router.storage_service,
        "delete",
        delete_from_storage,
    )

    with pytest.raises(RuntimeError, match="database failed"):
        await client.delete(
            "/api/files/42",
            headers=admin_headers,
        )

    delete_from_storage.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_image_rejects_invalid_id(
    client,
    admin_headers,
    monkeypatch,
):
    delete_file = AsyncMock()
    monkeypatch.setattr(file_router.file_service, "delete", delete_file)

    response = await client.delete(
        "/api/files/not-an-id",
        headers=admin_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json()["detail"][0]["loc"] == ["path", "file_id"]
    delete_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_image_rejects_non_admin(
    client,
    auth_headers,
    monkeypatch,
):
    delete_file = AsyncMock()
    monkeypatch.setattr(file_router.file_service, "delete", delete_file)

    response = await client.delete(
        "/api/files/42",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": "You do not have permission to perform this action"
    }
    delete_file.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_image_requires_authentication(client, monkeypatch):
    delete_file = AsyncMock()
    monkeypatch.setattr(file_router.file_service, "delete", delete_file)

    response = await client.delete("/api/files/42")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}
    delete_file.assert_not_awaited()
