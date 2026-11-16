from hashlib import sha256
from pathlib import Path

from starlette.staticfiles import StaticFiles


def static_version(directory: Path) -> str:
    """Version the whole module graph, including relative JS/CSS imports."""
    digest = sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(directory).as_posix().encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()[:16]


class RevalidatingStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        # Applies to both 200 and 304, including legacy unversioned URLs.
        response.headers["Cache-Control"] = "no-cache"
        return response
