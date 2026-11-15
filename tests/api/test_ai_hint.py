import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.enums import SubmissionStatus
from app.models import AIHintUsage, AIModelHintUsage, Enrollment, Lesson, Section, Step, Submission, Task, User
from app.services import ai_hint as service
from tests.conftest import test_async_session_maker

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def hint_data(db, course_factory):
    user = User(email="hint@example.com", password_hash="unused", first_name="Иван", last_name="Петров",
                ai_assistance_enabled=True)
    course = await course_factory(slug="ai-hints", is_published=True)
    section = Section(course_id=course.id, title="Раздел", order=0)
    db.add_all([user, section])
    await db.flush()
    lesson = Lesson(section_id=section.id, title="Урок", order=0)
    db.add(lesson)
    await db.flush()
    step = Step(lesson_id=lesson.id, title="Сумма чисел", order=0, content={
        "version": 1, "layout": "two_columns",
        "left": [{"type": "text", "data": {"text": "Прочитайте два числа и выведите сумму."}}],
        "right": [{"type": "code", "data": {"language": "python", "code": "# пример ввода"}}],
    })
    db.add(step)
    await db.flush()
    task = Task(step_id=step.id)
    db.add(task)
    await db.flush()
    submission = Submission(task_id=task.id, user_id=user.id, source_code="a = input()\nprint(a + a)",
                            status=SubmissionStatus.WRONG_ANSWER, passed_tests=0, total_tests=2,
                            actual_output="22")
    db.add_all([submission, Enrollment(user_id=user.id, course_id=course.id)])
    await db.commit()
    return {
        "user_id": user.id, "task_id": task.id, "submission_id": submission.id,
        "course_id": course.id,
        "headers": {"Authorization": f"Bearer {create_access_token(user.id)}"},
        "url": f"/api/submissions/{submission.id}/hint",
    }


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(settings, "ai_models", [])
    monkeypatch.setattr(settings, "ai_model", "vendor/test-model")
    monkeypatch.setattr(settings, "ai_api_key", SecretStr("test-provider-key"))
    state = {"requests": [], "status": 200, "body": {
        "choices": [{"message": {"content": "Проверь тип значения после input(): это строка."}}]
    }}
    real_client = httpx.AsyncClient

    def handle(request):
        state["requests"].append(request)
        if state.get("exception"):
            raise state["exception"]
        return httpx.Response(state["status"], json=state["body"])

    transport = httpx.MockTransport(handle)
    monkeypatch.setattr(service.httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs))
    return state


async def usage_count(db, user_id):
    return await db.scalar(select(AIHintUsage.requests_count).where(
        AIHintUsage.user_id == user_id, AIHintUsage.day == service.quota_period()[0]
    )) or 0


async def test_hint_payload_persistence_and_cached_response(client, db, hint_data, provider):
    response = await client.post(hint_data["url"], headers=hint_data["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["remaining"] == 9 and data["daily_limit"] == 10
    assert "тип" in data["hint"]
    request = provider["requests"][0]
    import json
    payload = json.loads(request.content)
    assert str(request.url) == service.AI_ENDPOINT
    assert request.headers["Authorization"] == "Bearer test-provider-key"
    assert payload["model"] == "vendor/test-model"
    material = json.loads(payload["messages"][1]["content"])
    assert "Прочитайте два числа" in material["task"]
    assert "# пример ввода" in material["task"]
    assert material["source_code"] == "a = input()\nprint(a + a)"
    assert material["diagnostics"] == "22"
    assert "email" not in material and "tests" not in material
    assert await usage_count(db, hint_data["user_id"]) == 1
    repeated = await client.post(hint_data["url"], headers=hint_data["headers"])
    assert repeated.json() == data
    assert len(provider["requests"]) == 1
    submission = await client.get(f"/api/submissions/{hint_data['submission_id']}", headers=hint_data["headers"])
    assert submission.json()["ai_hint"] == data["hint"]
    assert submission.json()["ai_hint_model"] == data["model"] == "vendor/test-model"


async def test_admin_can_grant_and_revoke_but_student_cannot(client, db, hint_data, admin_headers):
    path = f"/api/admin/users/{hint_data['user_id']}/ai-assistance"
    assert (await client.patch(path, json={"enabled": False})).status_code == 401
    assert (await client.patch(path, headers=hint_data["headers"], json={"enabled": False})).status_code == 403
    for enabled in (False, True):
        response = await client.patch(path, headers=admin_headers, json={"enabled": enabled})
        assert response.status_code == 200
        assert response.json()["ai_assistance_enabled"] is enabled
        status = await client.get("/api/submissions/ai-hints/status", headers=hint_data["headers"])
        assert status.json()["enabled"] is enabled
    assert (await client.patch(path, headers=admin_headers, json={"enabled": True, "role": "admin"})).status_code == 422
    assert (await client.patch("/api/admin/users/99999/ai-assistance", headers=admin_headers, json={"enabled": True})).status_code == 404
    listed = (await client.get("/api/admin/users", headers=admin_headers)).json()["items"]
    assert next(item for item in listed if item["id"] == hint_data["user_id"])["ai_assistance_enabled"] is True


async def test_access_and_default_disabled(client, db, hint_data, auth_headers, provider):
    assert (await client.post(hint_data["url"])).status_code == 401
    default_status = await client.get("/api/submissions/ai-hints/status", headers=auth_headers)
    assert default_status.json()["enabled"] is False
    user = await db.get(User, hint_data["user_id"])
    user.ai_assistance_enabled = False
    await db.commit()
    assert (await client.post(hint_data["url"], headers=hint_data["headers"])).status_code == 403
    assert not provider["requests"]


async def test_other_users_and_missing_submissions(client, db, hint_data, provider):
    other = User(email="other-hint@example.com", password_hash="unused", first_name="Other", last_name="User",
                 ai_assistance_enabled=True)
    db.add(other)
    await db.commit()
    headers = {"Authorization": f"Bearer {create_access_token(other.id)}"}
    assert (await client.post(hint_data["url"], headers=headers)).status_code == 404
    assert (await client.post("/api/submissions/999999/hint", headers=hint_data["headers"])).status_code == 404
    assert not provider["requests"]


@pytest.mark.parametrize("restriction", ["enrollment", "unpublished", "blocked"])
async def test_course_and_account_restrictions(client, db, hint_data, provider, restriction):
    if restriction == "enrollment":
        enrollment = await db.scalar(select(Enrollment).where(Enrollment.user_id == hint_data["user_id"]))
        await db.delete(enrollment)
    elif restriction == "unpublished":
        from app.models import Course
        course = await db.get(Course, hint_data["course_id"])
        course.is_published = False
    else:
        user = await db.get(User, hint_data["user_id"])
        user.blocked_at = datetime.now(UTC)
    await db.commit()
    response = await client.post(hint_data["url"], headers=hint_data["headers"])
    assert response.status_code == (404 if restriction == "unpublished" else 403)
    assert not provider["requests"]


@pytest.mark.parametrize("status", list(SubmissionStatus))
async def test_eligible_statuses(client, db, hint_data, provider, status):
    submission = await db.get(Submission, hint_data["submission_id"])
    submission.status = status
    await db.commit()
    response = await client.post(hint_data["url"], headers=hint_data["headers"])
    assert response.status_code == (200 if status in service.ELIGIBLE_STATUSES else 409)
    assert len(provider["requests"]) == (1 if status in service.ELIGIBLE_STATUSES else 0)


async def test_daily_limit_across_submissions_and_old_hint_still_available(client, db, hint_data, provider):
    first_hint = (await client.post(hint_data["url"], headers=hint_data["headers"])).json()["hint"]
    for count in range(2, 12):
        submission = Submission(task_id=hint_data["task_id"], user_id=hint_data["user_id"],
                                source_code="print('wrong')", status=SubmissionStatus.WRONG_ANSWER)
        db.add(submission)
        await db.commit()
        response = await client.post(f"/api/submissions/{submission.id}/hint", headers=hint_data["headers"])
        if count <= 10:
            assert response.status_code == 200
            assert response.json()["remaining"] == 10 - count
        else:
            assert response.status_code == 429
    assert len(provider["requests"]) == 10
    cached = await client.post(hint_data["url"], headers=hint_data["headers"])
    assert cached.status_code == 200 and cached.json()["hint"] == first_hint
    assert await usage_count(db, hint_data["user_id"]) == 10


@pytest.mark.parametrize("provider_status", [400, 401, 402, 403, 404, 429, 500, 502, 503, 504])
async def test_provider_errors_do_not_consume_quota(client, db, hint_data, provider, provider_status):
    provider["status"] = provider_status
    provider["body"] = {"error": "private upstream details"}
    response = await client.post(hint_data["url"], headers=hint_data["headers"])
    assert response.status_code == 503
    assert "private upstream" not in response.text
    assert "не израсходован" in response.json()["detail"]
    assert await usage_count(db, hint_data["user_id"]) == 0
    assert await db.scalar(select(AIModelHintUsage.requests_count).where(AIModelHintUsage.user_id == hint_data["user_id"])) is None
    provider["status"] = 200
    provider["body"] = {"choices": [{"message": {"content": "Проверь преобразование строки в число."}}]}
    assert (await client.post(hint_data["url"], headers=hint_data["headers"])).status_code == 200


@pytest.mark.parametrize("exception,expected", [
    (httpx.ReadTimeout("timeout"), 504), (httpx.ConnectError("connection refused"), 503),
])
async def test_network_errors(client, db, hint_data, provider, exception, expected):
    provider["exception"] = exception
    response = await client.post(hint_data["url"], headers=hint_data["headers"])
    assert response.status_code == expected
    assert await usage_count(db, hint_data["user_id"]) == 0


@pytest.mark.parametrize("body", [{}, {"choices": []}, {"choices": [{"message": {"content": None}}]},
                                  {"choices": [{"message": {"content": " "}}]},
                                  {"choices": [{"message": {"content": "x" * 4001}}]}])
async def test_malformed_answers(client, db, hint_data, provider, body):
    provider["body"] = body
    response = await client.post(hint_data["url"], headers=hint_data["headers"])
    assert response.status_code == 502
    assert await usage_count(db, hint_data["user_id"]) == 0


async def test_missing_configuration_and_source_limit(client, db, hint_data, provider, monkeypatch):
    monkeypatch.setattr(settings, "ai_model", "")
    assert (await client.post(hint_data["url"], headers=hint_data["headers"])).status_code == 503
    monkeypatch.setattr(settings, "ai_model", "vendor/test")
    monkeypatch.setattr(settings, "ai_api_key", SecretStr(""))
    assert (await client.post(hint_data["url"], headers=hint_data["headers"])).status_code == 503
    submission = await db.get(Submission, hint_data["submission_id"])
    submission.source_code = "#" * 30_001
    await db.commit()
    assert (await client.post(hint_data["url"], headers=hint_data["headers"])).status_code == 413
    assert not provider["requests"]


async def test_quota_resets_on_moscow_calendar_day(client, db, hint_data, monkeypatch):
    yesterday = service.quota_period()[0] - timedelta(days=1)
    db.add(AIHintUsage(user_id=hint_data["user_id"], day=yesterday, requests_count=10))
    await db.commit()
    status = (await client.get("/api/submissions/ai-hints/status", headers=hint_data["headers"])).json()
    assert status["remaining"] == 10
    assert status["resets_at"].endswith("T00:00:00+03:00")
    real_datetime = datetime

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 11, 15, 21, 1, tzinfo=UTC)

    monkeypatch.setattr(service, "datetime", FrozenDateTime)
    day, reset = service.quota_period()
    assert day.isoformat() == "2026-11-16"
    assert reset.isoformat() == "2026-11-17T00:00:00+03:00"


async def test_simultaneous_requests_and_cancellation_release_reservation(db, hint_data, provider, monkeypatch):
    entered = asyncio.Event()
    finish = asyncio.Event()

    async def slow_hint(*args):
        entered.set()
        await finish.wait()
        return "Проверь тип данных."

    monkeypatch.setattr(service, "request_hint", slow_hint)
    async with test_async_session_maker() as first, test_async_session_maker() as second:
        user_one = await first.get(User, hint_data["user_id"])
        task = asyncio.create_task(service.create_hint(first, user_one, hint_data["submission_id"]))
        await asyncio.wait_for(entered.wait(), timeout=3)
        try:
            user_two = await second.get(User, hint_data["user_id"])
            with pytest.raises(HTTPException) as busy:
                await service.create_hint(second, user_two, hint_data["submission_id"])
            assert busy.value.status_code == 409
        finally:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
    assert await usage_count(db, hint_data["user_id"]) == 0
    assert await db.scalar(select(AIModelHintUsage.requests_count).where(AIModelHintUsage.user_id == hint_data["user_id"])) is None
    monkeypatch.setattr(service, "request_hint", AsyncMock(return_value="Проверь тип данных."))
    async with test_async_session_maker() as retry:
        user = await retry.get(User, hint_data["user_id"])
        assert (await service.create_hint(retry, user, hint_data["submission_id"])).remaining == 9


@pytest.fixture
def multi_models(provider, monkeypatch):
    models = ["vendor/mini", "vendor/flash", "vendor/oss"]
    monkeypatch.setattr(settings, "ai_models", models)
    return models


async def another_submission(db, data):
    submission = Submission(task_id=data["task_id"], user_id=data["user_id"],
                            source_code="print('wrong')", status=SubmissionStatus.WRONG_ANSWER)
    db.add(submission)
    await db.commit()
    return f"/api/submissions/{submission.id}/hint"


async def set_policy(client, data, headers, *, daily_limit=4, model_limits=None):
    return await client.patch(f"/api/admin/users/{data['user_id']}/ai-assistance", headers=headers,
                              json={"enabled": True, "daily_limit": daily_limit,
                                    "model_limits": model_limits or {"vendor/mini": 1, "vendor/flash": 2, "vendor/oss": 1}})


async def test_model_catalog_and_allocations(client, db, hint_data, multi_models, admin_headers):
    assert (await client.get("/api/admin/ai-models")).status_code == 401
    assert (await client.get("/api/admin/ai-models", headers=hint_data["headers"])).status_code == 403
    assert (await client.get("/api/admin/ai-models", headers=admin_headers)).json() == multi_models
    response = await set_policy(client, hint_data, admin_headers)
    assert response.status_code == 200
    assert response.json()["ai_daily_limit"] == 4
    assert response.json()["ai_model_limits"] == {"vendor/mini": 1, "vendor/flash": 2, "vendor/oss": 1}
    status = (await client.get("/api/submissions/ai-hints/status", headers=hint_data["headers"])).json()
    assert status["remaining"] == status["daily_limit"] == 4
    assert status["models"] == [
        {"model": model, "daily_limit": limit, "remaining": limit}
        for model, limit in zip(multi_models, (1, 2, 1))
    ]


async def test_per_model_quota_total_quota_and_cached_model(client, db, hint_data, multi_models, provider, admin_headers):
    assert (await set_policy(client, hint_data, admin_headers)).status_code == 200
    headers = hint_data["headers"]
    response = await client.post(hint_data["url"], headers=headers, json={"model": "vendor/mini"})
    assert response.status_code == 200 and response.json()["remaining"] == 3
    next_url = await another_submission(db, hint_data)
    denied = await client.post(next_url, headers=headers, json={"model": "vendor/mini"})
    assert denied.status_code == 429 and "модели" in denied.json()["detail"]
    assert await usage_count(db, hint_data["user_id"]) == 1
    assert len(provider["requests"]) == 1
    for model in ("vendor/flash", "vendor/flash", "vendor/oss"):
        response = await client.post(next_url, headers=headers, json={"model": model})
        assert response.status_code == 200
        next_url = await another_submission(db, hint_data)
    assert response.json()["remaining"] == 0
    assert (await client.post(next_url, headers=headers, json={"model": "vendor/flash"})).status_code == 429
    cached = await client.post(hint_data["url"], headers=headers, json={"model": "vendor/flash"})
    assert cached.status_code == 200 and cached.json()["model"] == "vendor/mini"
    assert len(provider["requests"]) == 4
    import json
    assert [json.loads(request.content)["model"] for request in provider["requests"]] == [
        "vendor/mini", "vendor/flash", "vendor/flash", "vendor/oss"
    ]
    detail = (await client.get(f"/api/admin/submissions/{hint_data['submission_id']}", headers=admin_headers)).json()
    assert detail["ai_hint_model"] == "vendor/mini"


@pytest.mark.parametrize("changes", [
    {"daily_limit": 0}, {"daily_limit": 1001}, {"daily_limit": None}, {"model_limits": None},
    {"model_limits": {}}, {"model_limits": {"vendor/mini": 0}}, {"model_limits": {"vendor/mini": -1}},
    {"model_limits": {"vendor/mini": 1.5}}, {"model_limits": {"vendor/mini": "4"}},
    {"model_limits": {"vendor/unknown": 4}}, {"model_limits": {"vendor/mini": 3}},
    {"model_limits": {"vendor/mini": 5}},
])
async def test_invalid_allocations_are_not_saved(client, db, hint_data, multi_models, admin_headers, changes):
    payload = {"enabled": True, "daily_limit": 4, "model_limits": {"vendor/mini": 4}, **changes}
    response = await client.patch(f"/api/admin/users/{hint_data['user_id']}/ai-assistance", headers=admin_headers, json=payload)
    assert response.status_code == 422
    user = await db.get(User, hint_data["user_id"])
    assert user.ai_daily_limit == 10 and user.ai_model_limits is None


async def test_client_cannot_choose_an_unallocated_model(client, db, hint_data, multi_models, provider, admin_headers):
    assert (await set_policy(client, hint_data, admin_headers, model_limits={"vendor/mini": 4})).status_code == 200
    for model in ("vendor/flash", "vendor/unknown"):
        response = await client.post(hint_data["url"], headers=hint_data["headers"], json={"model": model})
        assert response.status_code == 422
    assert not provider["requests"]
    assert await usage_count(db, hint_data["user_id"]) == 0


async def test_policy_changes_and_env_reordering_preserve_spent_requests(client, db, hint_data, multi_models, provider, admin_headers, monkeypatch):
    assert (await set_policy(client, hint_data, admin_headers)).status_code == 200
    assert (await client.post(hint_data["url"], headers=hint_data["headers"], json={"model": "vendor/mini"})).status_code == 200
    assert (await set_policy(client, hint_data, admin_headers, daily_limit=5,
                             model_limits={"vendor/mini": 2, "vendor/flash": 2, "vendor/oss": 1})).status_code == 200
    monkeypatch.setattr(settings, "ai_models", list(reversed(multi_models)))
    status = (await client.get("/api/submissions/ai-hints/status", headers=hint_data["headers"])).json()
    assert status["remaining"] == 4
    assert next(item for item in status["models"] if item["model"] == "vendor/mini")["remaining"] == 1
    assert (await client.patch(f"/api/admin/users/{hint_data['user_id']}/ai-assistance", headers=admin_headers,
                               json={"enabled": False})).status_code == 200
    assert (await client.patch(f"/api/admin/users/{hint_data['user_id']}/ai-assistance", headers=admin_headers,
                               json={"enabled": True})).status_code == 200
    next_url = await another_submission(db, hint_data)
    assert (await client.post(next_url, headers=hint_data["headers"], json={"model": "vendor/mini"})).status_code == 200
    assert (await client.post(await another_submission(db, hint_data), headers=hint_data["headers"],
                              json={"model": "vendor/mini"})).status_code == 429


async def test_removed_models_and_service_errors_do_not_spend_budgets(client, db, hint_data, multi_models, provider, admin_headers, monkeypatch):
    assert (await set_policy(client, hint_data, admin_headers)).status_code == 200
    monkeypatch.setattr(settings, "ai_models", ["vendor/mini", "vendor/flash"])
    response = await client.post(hint_data["url"], headers=hint_data["headers"], json={"model": "vendor/oss"})
    assert response.status_code == 422
    provider["status"] = 503
    assert (await client.post(hint_data["url"], headers=hint_data["headers"], json={"model": "vendor/mini"})).status_code == 503
    assert await usage_count(db, hint_data["user_id"]) == 0
    assert await db.scalar(select(AIModelHintUsage.requests_count).where(AIModelHintUsage.user_id == hint_data["user_id"])) is None


async def test_custom_daily_limit_can_exceed_ten(client, db, hint_data, multi_models, provider, admin_headers):
    assert (await set_policy(client, hint_data, admin_headers, daily_limit=12, model_limits={"vendor/mini": 12})).status_code == 200
    url = hint_data["url"]
    for remaining in range(11, -1, -1):
        response = await client.post(url, headers=hint_data["headers"], json={"model": "vendor/mini"})
        assert response.status_code == 200 and response.json()["remaining"] == remaining
        url = await another_submission(db, hint_data)
    assert (await client.post(url, headers=hint_data["headers"], json={"model": "vendor/mini"})).status_code == 429


async def test_model_quotas_reset_on_the_next_day(client, db, hint_data, multi_models, admin_headers):
    assert (await set_policy(client, hint_data, admin_headers)).status_code == 200
    yesterday = service.quota_period()[0] - timedelta(days=1)
    db.add(AIHintUsage(user_id=hint_data["user_id"], day=yesterday, requests_count=4))
    db.add(AIModelHintUsage(user_id=hint_data["user_id"], day=yesterday, model="vendor/mini", requests_count=1))
    await db.commit()
    status = (await client.get("/api/submissions/ai-hints/status", headers=hint_data["headers"])).json()
    assert status["remaining"] == 4
    assert [item["remaining"] for item in status["models"]] == [1, 2, 1]
