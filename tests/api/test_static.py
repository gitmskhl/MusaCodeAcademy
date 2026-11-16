import re
from urllib.parse import urljoin, urlsplit

import pytest

from app.main import app

pytestmark = pytest.mark.asyncio


async def test_versioned_and_legacy_assets_revalidate_including_304(client):
    versioned = str(app.url_path_for("static", path="js/admin-user-actions.js"))
    assert re.match(r"/static/v-[0-9a-f]{16}/js/", versioned)
    responses = []
    for path in (versioned, "/static/js/admin-user-actions.js"):
        response = await client.get(path)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-cache"
        assert "export function createDeleteHomeworkButton" in response.text
        cached = await client.get(path, headers={"If-None-Match": response.headers["etag"]})
        assert cached.status_code == 304 and cached.headers["cache-control"] == "no-cache"
        responses.append(response.text)
    assert responses[0] == responses[1]


@pytest.mark.parametrize("path,entry", [
    ("/admin", "admin.js"), ("/admin/users", "admin-monitoring.js"),
    ("/admin/submissions", "admin-monitoring.js"), ("/admin/notifications", "admin-notifications.js"),
])
async def test_admin_pages_load_through_independent_versioned_bootstrap(client, path, entry):
    html = (await client.get(path)).text
    script = re.search(r'<script[^>]+src="([^"]+/js/admin-bootstrap.js)"[^>]+data-admin-entry="([^"]+)"', html)
    assert script is not None and script[2] == entry
    url = urlsplit(script[1]).path
    assert "/static/v-" in url
    assert (await client.get(url)).status_code == 200
    main = await client.get(urljoin(url, entry))
    assert main.status_code == 200
    if entry == "admin-monitoring.js":
        homework_url = urljoin(url, "admin-homework.js")
        homework = await client.get(homework_url)
        assert homework.status_code == 200
        assert "import { createDeleteHomeworkButton } from './admin-user-actions.js'" in homework.text
        actions = await client.get(urljoin(homework_url, "admin-user-actions.js"))
        assert "export function createDeleteHomeworkButton" in actions.text
