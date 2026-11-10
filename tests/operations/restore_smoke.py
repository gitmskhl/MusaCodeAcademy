"""Run explicitly: python tests/operations/restore_smoke.py (requires a built app image).

Creates and removes its own Compose project. Never uses the working project's DB.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from uuid import uuid4


def main():
    root = Path(__file__).resolve().parents[2]
    docker = shutil.which("docker")
    if not docker:
        raise SystemExit("Docker is required")
    with tempfile.TemporaryDirectory(prefix="mca-restore-smoke-") as temporary:
        directory = Path(temporary)
        (directory / "scripts").mkdir()
        script = directory / "scripts/restore-server.sh"
        shutil.copy2(root / "scripts/restore-server.sh", script)
        environment = {
            "SQLALCHEMY_DATABASE_URL": "postgresql+asyncpg://smoke:smoke@postgres:5432/academy",
            "REDIS_URL": "redis://redis:6379/0", "SECRET_KEY": "restore-smoke-test-secret-key",
            "ALGORITHM": "HS256", "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
            "SMTP_HOST": "localhost", "SMTP_PORT": "1025", "SMTP_USERNAME": "smoke",
            "SMTP_PASSWORD": "smoke", "SMTP_FROM": "smoke@example.com", "FRONTEND_URL": "http://localhost",
        }
        app = {
            "image": "musacodeacademy-app", "environment": environment,
            "volumes": [f"{root / 'app'}:/app/app:ro"],
            "command": ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"],
            "healthcheck": {"test": ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/openapi.json', timeout=3)"], "interval": "1s", "timeout": "4s", "retries": 30},
        }
        configuration = {"services": {
            "postgres": {"image": "postgres:17", "environment": {"POSTGRES_USER": "smoke", "POSTGRES_PASSWORD": "smoke", "POSTGRES_DB": "academy"},
                         "healthcheck": {"test": ["CMD", "pg_isready", "-U", "smoke", "-d", "academy"], "interval": "1s", "retries": 30}},
            "redis": {"image": "redis:7"}, "app": app,
            # No actual code execution or access to the host Docker socket in this test.
            "worker": {**app, "healthcheck": {"disable": True}, "command": ["python", "-c", "import signal,time; signal.signal(signal.SIGTERM, lambda *_: exit(0)); time.sleep(86400)"]},
        }}
        config = directory / "compose.json"
        config.write_text(json.dumps(configuration))
        env = {**os.environ, "COMPOSE_FILE": str(config), "COMPOSE_PROJECT_NAME": f"mca-smoke-{uuid4().hex[:10]}"}

        def compose(*args, **kwargs):
            return subprocess.run([docker, "compose", *args], env=env, cwd=directory,
                                  check=True, capture_output=True, **kwargs).stdout

        def sql(query):
            return compose("exec", "-T", "postgres", "psql", "-X", "-U", "smoke", "-d", "academy", "-v", "ON_ERROR_STOP=1", "-Atc", query).decode().strip()

        def restore(archive, *, extra_env=None, expected_success=True):
            result = subprocess.run([str(script), "--yes", str(archive)], cwd=directory,
                                    env={**env, **(extra_env or {})}, capture_output=True, text=True)
            if (result.returncode == 0) != expected_success:
                logs = "\n".join(path.read_text() for path in directory.glob("backups/*/restore.log"))
                raise AssertionError(f"{result.stdout}\n{result.stderr}\n{logs}")
            return result

        def healthy():
            compose("up", "-d", "--no-deps", "--wait", "--wait-timeout", "60", "app", "worker")

        try:
            compose("up", "-d", "--wait", "--wait-timeout", "60", "postgres", "redis")
            healthy()
            sql("CREATE TABLE restore_marker (value text); INSERT INTO restore_marker VALUES ('from_dump')")
            archive = directory / "source.dump"
            archive.write_bytes(compose("exec", "-T", "postgres", "pg_dump", "-U", "smoke", "-d", "academy", "-Fc"))
            sql("UPDATE restore_marker SET value = 'before_restore'")
            compose("exec", "-T", "redis", "redis-cli", "LPUSH", "submission_queue", "999999")
            compose("exec", "-T", "redis", "redis-cli", "SET", "unrelated", "keep")
            restore(archive)
            assert sql("SELECT value FROM restore_marker") == "from_dump"
            assert compose("exec", "-T", "redis", "redis-cli", "LLEN", "submission_queue").strip() == b"0"
            assert compose("exec", "-T", "redis", "redis-cli", "GET", "unrelated").strip() == b"keep"
            before = next(directory.glob("backups/*/before.dump"))
            backup_sql = compose("exec", "-T", "postgres", "pg_restore", "--data-only", "--table=restore_marker", "--file=-", input=before.read_bytes())
            assert b"before_restore" in backup_sql
            healthy()
            print("PASS: full replacement, previous backup, queue reconciliation, healthy startup")

            damaged = directory / "damaged.dump"
            damaged.write_bytes(archive.read_bytes()[:len(archive.read_bytes()) // 2])
            sql("UPDATE restore_marker SET value = 'keep_on_error'")
            started = compose("ps", "-q", "app").strip()
            restore(damaged, expected_success=False)
            assert sql("SELECT value FROM restore_marker") == "keep_on_error"
            assert compose("ps", "-q", "app").strip() == started
            print("PASS: damaged archive rejected without replacing the working database")

            # Fail exactly the first attempt to start app after the name swap.
            binary = directory / "bin"
            binary.mkdir()
            marker = directory / "fail-once"
            marker.touch()
            wrapper = binary / "docker"
            wrapper.write_text("#!/usr/bin/env python3\nimport os,sys\nfrom pathlib import Path\n"
                               f"marker=Path({str(marker)!r})\nargs=sys.argv[1:]\n"
                               "if 'up' in args and args[-1:] == ['app'] and marker.exists():\n    marker.unlink()\n    sys.exit(42)\n"
                               f"os.execv({docker!r}, [{docker!r}, *args])\n")
            wrapper.chmod(0o700)
            failed = restore(archive, extra_env={"PATH": f"{binary}:{os.environ['PATH']}"}, expected_success=False)
            assert "Прежняя база возвращена" in failed.stderr
            assert sql("SELECT value FROM restore_marker") == "keep_on_error"
            healthy()
            assert not sql("SELECT datname FROM pg_database WHERE datname LIKE 'mca_restore_%' OR datname LIKE 'mca_previous_%'")
            print("PASS: startup failure rolls back to the previous database and restarts services")
        finally:
            compose("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()
