import asyncio
from datetime import UTC, datetime
import shutil
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import make_url, select

from app.core.config import settings
from app.enums import UserRole
from app.models import User
from app.services import database_backup
from tests.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.asyncio


async def test_export_requires_active_admin(client, auth_headers, admin_headers, db, monkeypatch):
    create = AsyncMock()
    monkeypatch.setattr("app.api.routers.admin.create_database_backup", create)
    assert (await client.post("/api/admin/database/export")).status_code == 401
    user = await db.scalar(select(User))
    user.role = UserRole.STUDENT
    await db.commit()
    assert (await client.post("/api/admin/database/export", headers=auth_headers)).status_code == 403
    user.role = UserRole.ADMIN
    user.blocked_at = datetime.now(UTC)
    await db.commit()
    assert (await client.post("/api/admin/database/export", headers=admin_headers)).status_code == 403
    create.assert_not_awaited()


async def test_download_is_real_archive_private_and_removed(client, admin_headers, monkeypatch, tmp_path):
    if not shutil.which("pg_dump"):
        pytest.skip("PostgreSQL client is installed in the Docker app image")
    monkeypatch.setattr(settings, "sqlalchemy_database_url", TEST_DATABASE_URL)
    directory = tmp_path / "export"
    directory.mkdir(mode=0o700)
    monkeypatch.setattr(database_backup.tempfile, "mkdtemp", lambda **kwargs: str(directory))
    response = await client.post("/api/admin/database/export", headers=admin_headers)
    assert response.status_code == 200
    assert response.content.startswith(b"PGDMP")
    assert response.headers["cache-control"] == "no-store"
    assert '.dump"' in response.headers["content-disposition"]
    assert not directory.exists()
    archive = tmp_path / "download.dump"
    archive.write_bytes(response.content)
    listing = subprocess.run(["pg_restore", "--list", str(archive)], capture_output=True, check=True).stdout
    assert b"TABLE DATA public users" in listing
    assert b"TABLE DATA public courses" in listing


@pytest.mark.parametrize("failure", ["missing", "error", "timeout", "cancel"])
async def test_failed_export_cleans_files_and_releases_lock(monkeypatch, tmp_path, failure):
    monkeypatch.setattr(settings, "sqlalchemy_database_url", "postgresql+asyncpg://admin:secret@postgres/test")
    directory = tmp_path / "failed"
    directory.mkdir()
    monkeypatch.setattr(database_backup.tempfile, "mkdtemp", lambda **kwargs: str(directory))
    started = asyncio.Event()

    class Process:
        returncode = None

        async def wait(self):
            if self.returncode is not None:
                return self.returncode
            if failure == "error":
                self.returncode = 1
                return 1
            await asyncio.Event().wait()

        def kill(self):
            self.returncode = -9

    process = Process()

    async def create(*args, **kwargs):
        assert "secret" not in " ".join(args)
        assert kwargs["env"]["PGPASSWORD"] == "secret"
        if failure == "missing":
            raise FileNotFoundError()
        path = Path(next(arg.removeprefix("--file=") for arg in args if arg.startswith("--file=")))
        path.write_bytes(b"partial archive")
        started.set()
        return process

    monkeypatch.setattr(database_backup.asyncio, "create_subprocess_exec", create)
    monkeypatch.setattr(database_backup, "EXPORT_TIMEOUT_SECONDS", 0.01)
    task = asyncio.create_task(database_backup.create_database_backup())
    if failure == "cancel":
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as error:
            await task
        assert error.value.status_code == (504 if failure == "timeout" else 503)
        assert "secret" not in error.value.detail
    assert not directory.exists()
    assert not database_backup._export_lock.locked()


async def test_concurrent_export_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "sqlalchemy_database_url", "postgresql+asyncpg://admin:secret@postgres/test")
    from fastapi import HTTPException
    async with database_backup._export_lock:
        with pytest.raises(HTTPException) as error:
            await database_backup.create_database_backup()
    assert error.value.status_code == 409


async def test_interrupted_download_removes_private_archive(tmp_path):
    directory = tmp_path / "private"
    directory.mkdir()
    archive = directory / "database.dump"
    archive.write_bytes(b"PGDMP")
    response = database_backup.DatabaseBackupResponse(archive)

    async def send(message):
        raise OSError("client disconnected")

    with pytest.raises(OSError):
        await response({"type": "http", "method": "GET", "headers": []}, AsyncMock(), send)
    assert not directory.exists()
