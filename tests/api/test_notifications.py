import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.enums import UserRole
from app.models import Homework, Notification, User
from app.schemas.notification import HomeworkCreate
from app.services.notification import assign_homework, mark_read

pytestmark = pytest.mark.asyncio


def headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest_asyncio.fixture
async def students(db):
    users = [User(email=f"student{index}@example.com", first_name=name, last_name="Петров",
                  password_hash="unused", role=UserRole.STUDENT)
             for index, name in enumerate(("Иван", "Анна", "Муса"))]
    db.add_all(users)
    await db.commit()
    return users


def message(ids=None):
    return {"recipient_mode": "all" if ids is None else "selected", "recipient_ids": ids or [],
            "title": "  Новости школы  ", "text": "  <b>Занятие завтра</b>  "}


@pytest.mark.parametrize("method,path,payload", [
    ("GET", "/api/admin/notification-recipients", None),
    ("POST", "/api/admin/notifications/preview", {"recipient_mode": "all"}),
    ("POST", "/api/admin/notifications", message()),
    ("GET", "/api/admin/users/1/homework", None),
    ("POST", "/api/admin/users/1/homework", {"url": "/python/steps/1"}),
    ("DELETE", "/api/admin/users/1/homework/1", None),
])
async def test_only_admin_can_send_and_assign(client, auth_headers, method, path, payload):
    assert (await client.request(method, path, json=payload)).status_code == 401
    assert (await client.request(method, path, json=payload, headers=auth_headers)).status_code == 403


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/notifications"), ("POST", "/api/notifications/1/read"),
    ("POST", "/api/notifications/read-all"), ("GET", "/api/homework"),
    ("POST", "/api/homework/1/read-notification"),
])
async def test_personal_api_requires_login(client, method, path):
    assert (await client.request(method, path)).status_code == 401


@pytest.mark.parametrize("mode", ["one", "several", "all"])
async def test_delivery_preview_and_independent_read_status(client, db, admin_headers, students, mode):
    recipients = students[:1] if mode == "one" else students[:2] if mode == "several" else students
    payload = message(None if mode == "all" else [user.id for user in recipients])
    selection = {key: payload[key] for key in ("recipient_mode", "recipient_ids")}
    preview = await client.post("/api/admin/notifications/preview", json=selection, headers=admin_headers)
    assert preview.status_code == 200 and preview.json() == {"count": len(recipients)}
    assert await db.scalar(select(func.count()).select_from(Notification)) == 0
    response = await client.post("/api/admin/notifications", json=payload, headers=admin_headers)
    assert response.status_code == 201 and response.json() == {"count": len(recipients)}
    for user in students:
        inbox = (await client.get("/api/notifications", headers=headers(user))).json()
        expected = int(user in recipients)
        assert inbox["total"] == inbox["unread_count"] == expected
        if expected:
            item = inbox["items"][0]
            assert item["title"] == "Новости школы" and item["text"] == "<b>Занятие завтра</b>"
            assert item["read_at"] is None and item["homework"] is None
    # Reading a list or opening the bell never mutates read status.
    owner = headers(recipients[0])
    inbox = (await client.get("/api/notifications?page_size=10", headers=owner)).json()
    assert inbox["unread_count"] == 1
    notification_id = inbox["items"][0]["id"]
    first = await client.post(f"/api/notifications/{notification_id}/read", headers=owner)
    assert first.status_code == 200 and first.json()["read_at"] is not None
    second = await client.post(f"/api/notifications/{notification_id}/read", headers=owner)
    assert second.json()["read_at"] == first.json()["read_at"]
    assert (await client.get("/api/notifications", headers=owner)).json()["unread_count"] == 0
    for user in recipients[1:]:
        assert (await client.get("/api/notifications", headers=headers(user))).json()["unread_count"] == 1


async def test_search_students_by_name_email_and_pagination(client, admin_headers, students):
    for term, expected in [("иван петров", students[0]), ("STUDENT1@EXAMPLE", students[1])]:
        response = await client.get("/api/admin/notification-recipients", params={"q": term}, headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0] == {"id": expected.id, "first_name": expected.first_name,
                                                "last_name": expected.last_name, "email": expected.email}
    first = (await client.get("/api/admin/notification-recipients?page_size=1", headers=admin_headers)).json()
    second = (await client.get("/api/admin/notification-recipients?page_size=1&page=2", headers=admin_headers)).json()
    assert first["total"] == 3 and first["items"][0]["id"] != second["items"][0]["id"]
    assert (await client.get("/api/admin/notification-recipients?q=%25", headers=admin_headers)).json()["total"] == 0


async def test_duplicate_recipients_and_invalid_selection_are_atomic(client, db, admin_headers, students):
    actor = await db.scalar(select(User).where(User.role == UserRole.ADMIN))
    for ids in ([students[0].id, 999999], [actor.id]):
        payload = message(ids)
        assert (await client.post("/api/admin/notifications", json=payload, headers=admin_headers)).status_code == 422
        assert (await client.post("/api/admin/notifications/preview", json={"recipient_mode": "selected", "recipient_ids": ids}, headers=admin_headers)).status_code == 422
        assert await db.scalar(select(func.count()).select_from(Notification)) == 0
    response = await client.post("/api/admin/notifications", json=message([students[0].id] * 2), headers=admin_headers)
    assert response.status_code == 201 and response.json() == {"count": 1}
    assert await db.scalar(select(func.count()).select_from(Notification)) == 1


@pytest.mark.parametrize("changes", [
    {"recipient_mode": "selected", "recipient_ids": []}, {"recipient_mode": "unknown"},
    {"recipient_mode": "all", "recipient_ids": [1]}, {"recipient_ids": [-1]},
    {"title": "   "}, {"text": "\n "}, {"title": "x" * 256}, {"text": "x" * 10001},
    {"user_id": 1},
])
async def test_notification_validation(client, admin_headers, changes):
    assert (await client.post("/api/admin/notifications", json={**message(), **changes}, headers=admin_headers)).status_code == 422


async def test_empty_all_students_preview_and_send(client, admin_headers):
    assert (await client.post("/api/admin/notifications/preview", json={"recipient_mode": "all"}, headers=admin_headers)).json() == {"count": 0}
    assert (await client.post("/api/admin/notifications", json=message(), headers=admin_headers)).status_code == 422


async def test_pagination_read_all_and_cross_user_protection(client, db, admin_headers, students):
    now = datetime.now(UTC)
    db.add_all([Notification(user_id=user.id, title=f"Сообщение {i}", text="Текст", created_at=now)
                for user in students[:2] for i in range(23)])
    await db.commit()
    owner = headers(students[0])
    latest = (await client.get("/api/notifications?page_size=10", headers=owner)).json()
    first = (await client.get("/api/notifications", headers=owner)).json()
    second = (await client.get("/api/notifications?page=2", headers=owner)).json()
    assert len(latest["items"]) == 10 and latest["unread_count"] == 23
    assert first["total"] == first["unread_count"] == 23
    assert len(first["items"]) == 20 and len(second["items"]) == 3
    ids = [item["id"] for item in first["items"] + second["items"]]
    assert ids == sorted(ids, reverse=True) and len(set(ids)) == 23
    path = f"/api/notifications/{ids[0]}/read"
    for other in (headers(students[1]), admin_headers):
        assert (await client.post(path, headers=other)).status_code == 404
    assert (await client.post("/api/notifications/read-all", headers=owner)).status_code == 204
    assert (await client.get("/api/notifications", headers=owner)).json()["unread_count"] == 0
    assert (await client.get("/api/notifications", headers=headers(students[1]))).json()["unread_count"] == 23
    # Supplying another user's ID cannot change the scope of a personal list.
    assert (await client.get(f"/api/notifications?user_id={students[1].id}", headers=headers(students[2]))).json()["items"] == []


@pytest.mark.parametrize("url", ["/python/steps/12?task=4#editor", "/python/lessons/2/steps", "https://example.org/material?x=1&y=2", "http://example.org/lesson"])
async def test_homework_assignment_separate_notification_and_open(client, db, admin_headers, students, url):
    user, other = students[:2]
    payload = {"title": "Практика", "comment": "Реши первые две задачи", "url": url, "due_date": "2026-12-01"}
    response = await client.post(f"/api/admin/users/{user.id}/homework", json=payload, headers=admin_headers)
    assert response.status_code == 201
    homework = response.json()
    assert homework["url"] == url and homework["due_date"] == "2026-12-01"
    stored = await db.get(Homework, homework["id"])
    notice = await db.scalar(select(Notification).where(Notification.homework_id == stored.id))
    assert notice.user_id == stored.user_id == user.id and notice.read_at is None
    inbox = (await client.get("/api/notifications", headers=headers(user))).json()
    assert inbox["items"][0]["homework"] == homework
    admin_list = (await client.get(f"/api/admin/users/{user.id}/homework", headers=admin_headers)).json()
    mine = (await client.get("/api/homework", headers=headers(user))).json()
    assert admin_list["items"] == mine["items"] == [homework]
    assert (await client.get("/api/homework", headers=headers(other))).json()["items"] == []
    path = f"/api/homework/{stored.id}/read-notification"
    assert (await client.post(path, headers=headers(other))).status_code == 404
    assert (await client.post(path, headers=admin_headers)).status_code == 404
    assert (await client.post(path, headers=headers(user))).status_code == 204
    assert (await client.get("/api/notifications", headers=headers(user))).json()["unread_count"] == 0
    # Reading never changes or removes the assignment; there is no completion state.
    assert (await client.get("/api/homework", headers=headers(user))).json()["items"] == [homework]


async def test_homework_defaults_and_reading_notification(client, admin_headers, students):
    user = students[0]
    response = await client.post(f"/api/admin/users/{user.id}/homework", json={"url": "/python/steps/1", "comment": "  "}, headers=admin_headers)
    assert response.status_code == 201
    homework = response.json()
    assert homework["title"] == "Новое домашнее задание" and homework["comment"] is None and homework["due_date"] is None
    inbox = (await client.get("/api/notifications", headers=headers(user))).json()
    read = await client.post(f"/api/notifications/{inbox['items'][0]['id']}/read", headers=headers(user))
    assert read.status_code == 200 and read.json()["homework"] == homework
    assert (await client.get("/api/homework", headers=headers(user))).json()["total"] == 1


@pytest.mark.parametrize("read", [False, True])
async def test_delete_homework_removes_only_its_assignment_and_notification(client, db, admin_headers, students, read):
    user, other = students[:2]
    assignments = []
    for owner in (user, user, other):
        response = await client.post(f"/api/admin/users/{owner.id}/homework", json={"url": "/python/steps/1"}, headers=admin_headers)
        assert response.status_code == 201
        assignments.append(response.json()["id"])
    await client.post("/api/admin/notifications", json=message([user.id]), headers=admin_headers)
    if read:
        assert (await client.post(f"/api/homework/{assignments[0]}/read-notification", headers=headers(user))).status_code == 204
    response = await client.delete(f"/api/admin/users/{user.id}/homework/{assignments[0]}", headers=admin_headers)
    assert response.status_code == 204 and response.content == b""
    assert await db.scalar(select(Homework.id).where(Homework.id == assignments[0])) is None
    assert await db.scalar(select(Notification.id).where(Notification.homework_id == assignments[0])) is None
    mine = (await client.get("/api/homework", headers=headers(user))).json()
    assert [item["id"] for item in mine["items"]] == [assignments[1]]
    inbox = (await client.get("/api/notifications", headers=headers(user))).json()
    assert inbox["total"] == inbox["unread_count"] == 2
    assert (await client.get("/api/homework", headers=headers(other))).json()["items"][0]["id"] == assignments[2]
    assert (await client.get("/api/notifications", headers=headers(other))).json()["unread_count"] == 1
    assert (await client.post(f"/api/homework/{assignments[0]}/read-notification", headers=headers(user))).status_code == 404
    assert (await client.delete(f"/api/admin/users/{user.id}/homework/{assignments[0]}", headers=admin_headers)).status_code == 404


async def test_homework_deletion_checks_student_and_assignment_ownership(client, db, admin_headers, students):
    user, other = students[:2]
    created = await client.post(f"/api/admin/users/{user.id}/homework", json={"url": "/python"}, headers=admin_headers)
    homework_id = created.json()["id"]
    for user_id, record_id in ((other.id, homework_id), (999999, homework_id), (user.id, 999999)):
        response = await client.delete(f"/api/admin/users/{user_id}/homework/{record_id}", headers=admin_headers)
        assert response.status_code == 404
    assert await db.scalar(select(Homework.id).where(Homework.id == homework_id)) == homework_id
    assert (await client.get("/api/notifications", headers=headers(user))).json()["unread_count"] == 1


async def test_concurrent_read_preserves_first_timestamp(db, students):
    user_id = students[0].id
    notification = Notification(user_id=user_id, title="Новости", text="Текст")
    db.add(notification)
    await db.commit()
    notification_id = notification.id

    async def read():
        async with AsyncSession(db.bind, expire_on_commit=False) as session:
            result = await mark_read(session, user_id=user_id, notification_id=notification_id)
            return result.read_at

    first, second = await asyncio.gather(read(), read())
    assert first is not None and first == second


@pytest.mark.parametrize("url", ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,test", "file:///tmp/a", "vbscript:test", "//evil.example/a", "/\\evil.example/a", "/%5cevil", "/%2fevil", "https://", "https://[invalid", "https://example.org:bad", "https://example.org/\nx", "https://example.org/%0a", "relative/path", ""])
async def test_unsafe_links_are_rejected_without_partial_records(client, db, admin_headers, students, url):
    response = await client.post(f"/api/admin/users/{students[0].id}/homework", json={"url": url}, headers=admin_headers)
    assert response.status_code == 422
    for model in (Homework, Notification):
        assert await db.scalar(select(func.count()).select_from(model)) == 0


async def test_homework_validation_and_missing_students(client, db, admin_headers, students):
    actor = await db.scalar(select(User).where(User.role == UserRole.ADMIN))
    for user_id in (actor.id, 999999):
        assert (await client.post(f"/api/admin/users/{user_id}/homework", json={"url": "/python"}, headers=admin_headers)).status_code == 404
        assert (await client.get(f"/api/admin/users/{user_id}/homework", headers=admin_headers)).status_code == 404
    for payload in ({}, {"url": "/python", "title": "  "}, {"url": "/python", "due_date": "invalid"}, {"url": "/python", "user_id": students[1].id}):
        assert (await client.post(f"/api/admin/users/{students[0].id}/homework", json=payload, headers=admin_headers)).status_code == 422


async def test_failed_assignment_rolls_back_both_records(db, admin_headers, students, monkeypatch):
    actor = await db.scalar(select(User.id).where(User.role == UserRole.ADMIN))
    monkeypatch.setattr(db, "commit", AsyncMock(side_effect=RuntimeError("storage failed")))
    with pytest.raises(RuntimeError, match="storage failed"):
        await assign_homework(db, user_id=students[0].id, actor_id=actor, data=HomeworkCreate(url="/python"))
    for model in (Homework, Notification):
        assert await db.scalar(select(func.count()).select_from(model)) == 0
    monkeypatch.undo()


async def test_user_deletion_cascades_personal_records_preserves_assignments_by_deleted_admin(client, db, admin_headers, students):
    actor_id = await db.scalar(select(User.id).where(User.role == UserRole.ADMIN))
    user, other = students[:2]
    for owner in (user, other):
        await client.post(f"/api/admin/users/{owner.id}/homework", json={"url": "/python"}, headers=admin_headers)
    assert (await client.delete(f"/api/admin/users/{user.id}", headers=admin_headers)).status_code == 204
    for model in (Homework, Notification):
        assert await db.scalar(select(func.count()).select_from(model).where(model.user_id == user.id)) == 0
        assert await db.scalar(select(func.count()).select_from(model).where(model.user_id == other.id)) == 1
    actor = await db.get(User, actor_id)
    await db.delete(actor)
    await db.commit()
    remaining = await db.scalar(select(Homework).where(Homework.user_id == other.id).execution_options(populate_existing=True))
    assert remaining.assigned_by_id is None


@pytest.mark.parametrize("path", ["/api/notifications?page=0", "/api/notifications?page_size=101", "/api/homework?page=0"])
async def test_invalid_pagination(client, auth_headers, path):
    assert (await client.get(path, headers=auth_headers)).status_code == 422


@pytest.mark.parametrize("path,title", [("/notifications", "Все уведомления"), ("/homework", "Мои домашние задания"), ("/admin/notifications", "Отправить уведомление")])
async def test_page_routes_take_priority_over_course_slugs(client, path, title):
    response = await client.get(path)
    assert response.status_code == 200 and title in response.text
