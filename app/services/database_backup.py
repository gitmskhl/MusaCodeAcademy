"""Create a private PostgreSQL archive without exposing connection credentials."""

import asyncio
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import make_url
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

EXPORT_TIMEOUT_SECONDS = 300
_export_lock = asyncio.Lock()


class DatabaseBackupResponse(FileResponse):
    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            # Also remove the private archive when a download is interrupted.
            await run_in_threadpool(shutil.rmtree, Path(self.path).parent, ignore_errors=True)


async def create_database_backup() -> Path:
    url = make_url(settings.sqlalchemy_database_url)
    if url.get_backend_name() != "postgresql":
        raise HTTPException(503, "Экспорт доступен только для PostgreSQL.")
    if _export_lock.locked():
        raise HTTPException(409, "Экспорт уже выполняется. Попробуйте позже.")

    async with _export_lock:
        directory = Path(tempfile.mkdtemp(prefix="mca-backup-"))
        path = directory / f"musacodeacademy_{datetime.now(UTC):%Y-%m-%d_%H-%M-%S}_UTC.dump"
        env = os.environ.copy()
        # Pass libpq settings in the environment, never in argv or error responses.
        for key in list(env):
            if key.startswith("PG"):
                del env[key]
        env.update({
            "PGHOST": url.host or "localhost",
            "PGPORT": str(url.port or 5432),
            "PGDATABASE": url.database or "",
            "PGUSER": url.username or "",
            "PGPASSWORD": url.password or "",
            "PGCONNECT_TIMEOUT": "10",
        })
        process = None
        completed = False
        try:
            # stderr can contain credentials or personal data; do not log or return it.
            process = await asyncio.create_subprocess_exec(
                "pg_dump", "--format=custom", "--no-owner", "--no-privileges",
                "--no-password", f"--file={path}",
                env=env, stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                await asyncio.wait_for(process.wait(), timeout=EXPORT_TIMEOUT_SECONDS)
            except TimeoutError:
                raise HTTPException(504, "Экспорт занял слишком много времени. Попробуйте позже.") from None
            if process.returncode != 0 or not path.is_file() or path.stat().st_size == 0:
                raise HTTPException(503, "Не удалось создать копию БД. Проверьте доступность PostgreSQL.")
            path.chmod(0o600)
            completed = True
            return path
        except FileNotFoundError:
            raise HTTPException(503, "Для экспорта требуется pg_dump 17. Обновите образ приложения.") from None
        finally:
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
            # Successful archives are deleted after FileResponse finishes downloading.
            if not completed:
                shutil.rmtree(directory, ignore_errors=True)
