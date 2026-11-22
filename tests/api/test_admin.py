from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text

from app.core.security import create_access_token, hash_password
from app.enums import SubmissionStatus, UserRole
from app.models import (
    AIHintUsage, AIModelHintUsage, CourseActivity, Enrollment, Homework, Lesson, PasswordResetToken,
    Section, Step, StepProgress, Submission, Task, User,
)

pytestmark = pytest.mark.asyncio


async def make_user(db, email="student@example.com", **kwargs):
    user = User(email=email, password_hash=hash_password("12345678"), first_name="Иван", last_name="Петров", **kwargs)
    db.add(user)
    await db.commit()
    return user


def headers(user):
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest_asyncio.fixture
async def learning_data(db, course_factory):
    user = await make_user(db)
    course = await course_factory(slug="admin-python", title="Python", is_published=False)
    section = Section(course_id=course.id, title="Раздел", order=0)
    db.add(section)
    await db.flush()
    lesson = Lesson(section_id=section.id, title="Урок", order=0)
    db.add(lesson)
    await db.flush()
    steps = [Step(lesson_id=lesson.id, title=f"Шаг {index}", order=index, content={}) for index in range(3)]
    db.add_all(steps)
    await db.flush()
    tasks = [Task(step_id=step.id) for step in steps[:2]]
    db.add_all(tasks)
    await db.flush()
    attempts = [Submission(
        task_id=tasks[0].id, user_id=user.id, source_code="print('<script>alert(1)</script>')",
        status=SubmissionStatus.ACCEPTED, passed_tests=2, total_tests=2,
        submitted_at=datetime(2026, 11, 2, hour, tzinfo=UTC),
    ) for hour in (10, 11)]
    attempts.append(Submission(
        task_id=tasks[1].id, user_id=user.id, source_code="print('error')",
        status=SubmissionStatus.RUNTIME_ERROR, passed_tests=0, total_tests=2,
        failed_test_id=123, actual_output="<b>error</b>",
        submitted_at=datetime(2026, 11, 3, 0, tzinfo=UTC),
    ))
    db.add_all(attempts)
    db.add_all([
        Enrollment(user_id=user.id, course_id=course.id),
        StepProgress(user_id=user.id, step_id=steps[0].id, completed_at=datetime(2026, 11, 2, tzinfo=UTC)),
        CourseActivity(user_id=user.id, course_id=course.id, last_step_id=steps[1].id,
                       last_visited_at=datetime(2026, 11, 4, tzinfo=UTC)),
    ])
    await db.commit()
    return user, course, tasks, attempts


@pytest.mark.parametrize("method,path,payload", [
    ("GET", "/api/admin/users", None),
    ("GET", "/api/admin/users/1", None),
    ("PATCH", "/api/admin/users/1/block", {"blocked": True, "reason": "test"}),
    ("DELETE", "/api/admin/users/1", None),
    ("PUT", "/api/admin/users/1/courses/1", None),
    ("DELETE", "/api/admin/users/1/courses/1", None),
    ("GET", "/api/admin/submissions", None),
    ("GET", "/api/admin/submissions/1", None),
    ("GET", "/api/admin/courses", None),
    ("GET", "/api/admin/users/1/homework/latest-progress", None),
    ("GET", "/api/steps/1/viewer/admin?course_slug=python", None),
])
async def test_admin_access_required(client, auth_headers, method, path, payload):
    assert (await client.request(method, path, json=payload)).status_code == 401
    assert (await client.request(method, path, headers=auth_headers, json=payload)).status_code == 403


async def test_user_list_filters_and_pagination(client, db, admin_headers, learning_data):
    user, course, _, _ = learning_data
    blocked = await make_user(db, "blocked@example.com", blocked_at=datetime.now(UTC), block_reason="Причина")
    data = (await client.get("/api/admin/users", headers=admin_headers, params={"q": "иван петров", "blocked": False})).json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == user.id
    assert data["items"][0]["solved_tasks_count"] == 1
    assert data["items"][0]["submissions_count"] == 3
    assert "password_hash" not in data["items"][0]
    for params, expected_id in [
        ({"q": str(user.id)}, user.id), ({"q": "STUDENT@EXAMPLE"}, user.id),
        ({"blocked": True}, blocked.id), ({"course_id": course.id}, user.id),
    ]:
        result = await client.get("/api/admin/users", headers=admin_headers, params=params)
        assert result.status_code == 200
        assert [item["id"] for item in result.json()["items"]] == [expected_id]
    data = (await client.get("/api/admin/users?page_size=1&page=2", headers=admin_headers)).json()
    assert data["total"] == 3 and len(data["items"]) == 1 and data["page"] == 2
    assert (await client.get("/api/admin/users?q=%25", headers=admin_headers)).json()["total"] == 0
    assert (await client.get("/api/admin/users?q=9999999999", headers=admin_headers)).json()["total"] == 0
    assert (await client.get("/api/admin/users?role=admin", headers=admin_headers)).json()["total"] == 1


async def test_user_progress_counts_and_unenrolled_history(client, db, admin_headers, learning_data):
    user, course, _, _ = learning_data
    response = await client.get(f"/api/admin/users/{user.id}", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["submissions_count"] == 3
    assert data["solved_tasks_count"] == 1
    assert data["last_activity_at"].startswith("2026-11-04")
    progress = data["courses"][0]
    assert progress == {
        "id": course.id, "title": "Python", "is_published": False, "enrolled": True,
        "completed_steps": 1, "total_steps": 3, "solved_tasks": 1, "total_tasks": 2,
        "submissions_count": 3, "last_activity_at": "2026-11-04T00:00:00Z",
    }
    enrollment = await db.scalar(select(Enrollment).where(Enrollment.user_id == user.id))
    await db.delete(enrollment)
    await db.commit()
    data = (await client.get(f"/api/admin/users/{user.id}", headers=admin_headers)).json()
    assert data["courses"][0]["enrolled"] is False
    empty_user = await make_user(db, "empty@example.com")
    data = (await client.get(f"/api/admin/users/{empty_user.id}", headers=admin_headers)).json()
    assert data["courses"] == [] and data["submissions_count"] == 0 and data["last_activity_at"] is None


@pytest.mark.parametrize("table,column", [
    ("submissions", "submitted_at"),
    ("course_activity", "last_visited_at"),
    ("step_progress", "completed_at"),
])
async def test_user_card_with_legacy_timestamps(client, db, admin_headers, learning_data, table, column):
    user, _, _, _ = learning_data
    # Older installations can have timestamp columns without time zones even
    # though the current ORM declares DateTime(timezone=True).
    await db.execute(text(
        f"ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMP WITHOUT TIME ZONE "
        f"USING {column} AT TIME ZONE 'UTC'"
    ))
    await db.commit()
    try:
        response = await client.get(f"/api/admin/users/{user.id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["courses"][0]["last_activity_at"] == "2026-11-04T00:00:00Z"
    finally:
        await db.rollback()
        await db.execute(text(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE "
            f"USING {column} AT TIME ZONE 'UTC'"
        ))
        await db.commit()


@pytest.mark.parametrize("ai_hint", [None, "Проверь тип данных после input(). <b>Подсказка</b>"])
async def test_submission_filters_detail_and_stable_order(client, db, admin_headers, learning_data, ai_hint):
    user, course, tasks, attempts = learning_data
    # Equal timestamps must still produce stable pagination.
    attempts[1].submitted_at = attempts[0].submitted_at
    attempts[2].ai_hint = ai_hint
    await db.commit()
    data = (await client.get("/api/admin/submissions?page_size=2", headers=admin_headers)).json()
    assert data["total"] == 3
    assert data["items"][0]["course_slug"] == course.slug
    assert [item["id"] for item in data["items"]] == [attempts[2].id, attempts[1].id]
    assert "source_code" not in data["items"][0]
    assert "ai_hint" not in data["items"][0]
    params = {"user_id": user.id, "course_id": course.id, "task_id": tasks[0].id,
              "status": "ACCEPTED", "q": "Иван", "date_from": "2026-11-02", "date_to": "2026-11-02"}
    response = await client.get("/api/admin/submissions", headers=admin_headers, params=params)
    assert response.status_code == 200
    assert response.json()["total"] == 2
    dates_only = await client.get("/api/admin/submissions", headers=admin_headers,
                                  params={"date_from": "2026-11-02", "date_to": "2026-11-02"})
    assert [item["id"] for item in dates_only.json()["items"]] == [attempts[1].id, attempts[0].id]
    params["user_id"] = 99999
    assert (await client.get("/api/admin/submissions", headers=admin_headers, params=params)).json()["total"] == 0
    detail = (await client.get(f"/api/admin/submissions/{attempts[2].id}", headers=admin_headers)).json()
    assert detail["source_code"] == attempts[2].source_code
    assert detail["course_slug"] == course.slug
    assert detail["actual_output"] == "<b>error</b>"
    assert detail["ai_hint"] == ai_hint
    assert detail["user_email"] == user.email and detail["failed_test_id"] == 123
    assert "password_hash" not in detail


async def test_block_prevents_old_token_login_and_writes_preserves_history(client, db, admin_headers, learning_data):
    user, _, _, attempts = learning_data
    old_headers = headers(user)
    result = await client.patch(f"/api/admin/users/{user.id}/block", headers=admin_headers,
                                json={"blocked": True, "reason": "  Спам  "})
    assert result.status_code == 200
    assert result.json()["block_reason"] == "Спам"
    assert result.json()["blocked_at"] is not None
    assert (await client.get("/api/users/me", headers=old_headers)).status_code == 403
    assert (await client.get(f"/api/submissions/{attempts[0].id}", headers=old_headers)).status_code == 403
    assert (await client.post("/api/progress/steps/1", headers=old_headers)).status_code == 403
    assert (await client.post("/api/auth/token", data={"username": user.email, "password": "12345678"})).status_code == 403
    # Invalid credentials must not reveal the account's blocked status.
    assert (await client.post("/api/auth/token", data={"username": user.email, "password": "wrong"})).status_code == 401
    assert await db.scalar(select(func.count()).select_from(Submission).where(Submission.user_id == user.id)) == 3
    assert await db.scalar(select(func.count()).select_from(StepProgress).where(StepProgress.user_id == user.id)) == 1
    result = await client.patch(f"/api/admin/users/{user.id}/block", headers=admin_headers, json={"blocked": False})
    assert result.status_code == 200
    assert result.json()["blocked_at"] is None and result.json()["block_reason"] is None
    assert (await client.get("/api/users/me", headers=old_headers)).status_code == 200
    assert (await client.post("/api/auth/token", data={"username": user.email, "password": "12345678"})).status_code == 200


async def test_block_protection_and_validation(client, db, admin_headers):
    actor = await db.scalar(select(User).where(User.role == UserRole.ADMIN))
    assert (await client.patch(f"/api/admin/users/{actor.id}/block", headers=admin_headers,
                              json={"blocked": True, "reason": "test"})).status_code == 409
    user = await make_user(db)
    for payload in ({"blocked": True}, {"blocked": True, "reason": "   "},
                    {"blocked": True, "reason": "x" * 501}, {"blocked": False, "role": "admin"}):
        assert (await client.patch(f"/api/admin/users/{user.id}/block", headers=admin_headers, json=payload)).status_code == 422
    other_admin = await make_user(db, "admin2@example.com", role=UserRole.ADMIN)
    assert (await client.patch(f"/api/admin/users/{other_admin.id}/block", headers=admin_headers,
                              json={"blocked": True, "reason": "test"})).status_code == 200
    assert (await client.get("/api/admin/users", headers=headers(other_admin))).status_code == 403
    await db.refresh(actor)
    assert actor.blocked_at is None
    assert (await client.patch("/api/admin/users/999999/block", headers=admin_headers,
                              json={"blocked": True, "reason": "test"})).status_code == 404


@pytest.mark.parametrize("blocked", [False, True])
async def test_delete_user_removes_all_personal_data(client, db, admin_headers, learning_data, blocked):
    user, course, tasks, _ = learning_data
    user_id, email = user.id, user.email
    old_headers = headers(user)
    if blocked:
        user.blocked_at = datetime.now(UTC)
        user.block_reason = "Спам"
    other = await make_user(db, "keep@example.com")
    day = datetime.now(UTC).date()
    for owner in (user, other):
        db.add_all([
            PasswordResetToken(user_id=owner.id, token_hash=f"reset-{owner.id}", expires_at=datetime.now(UTC) + timedelta(hours=1)),
            AIHintUsage(user_id=owner.id, day=day, requests_count=1),
            AIModelHintUsage(user_id=owner.id, day=day, model="test-model", requests_count=1),
        ])
    db.add_all([
        Enrollment(user_id=other.id, course_id=course.id),
        Submission(user_id=other.id, task_id=tasks[0].id, source_code="print('keep')"),
        StepProgress(user_id=other.id, step_id=tasks[0].step_id),
        CourseActivity(user_id=other.id, course_id=course.id),
    ])
    await db.commit()
    response = await client.delete(f"/api/admin/users/{user_id}", headers=admin_headers)
    assert response.status_code == 204 and response.content == b""
    assert await db.scalar(select(User.id).where(User.id == user_id)) is None
    for model in (Enrollment, Submission, StepProgress, CourseActivity, PasswordResetToken, AIHintUsage, AIModelHintUsage):
        assert await db.scalar(select(func.count()).select_from(model).where(model.user_id == user_id)) == 0
        assert await db.scalar(select(func.count()).select_from(model).where(model.user_id == other.id)) == 1
    assert (await client.get(f"/api/admin/users/{user_id}", headers=admin_headers)).status_code == 404
    assert (await client.get("/api/users/me", headers=old_headers)).status_code == 401
    assert (await client.post("/api/auth/token", data={"username": email, "password": "12345678"})).status_code == 401
    # Full deletion frees the email, but the old JWT must not access a new account.
    result = await client.post("/api/auth/register", json={
        "email": email, "password": "12345678", "first_name": "Иван", "last_name": "Петров",
    })
    assert result.status_code == 201
    assert (await client.get("/api/users/me", headers=old_headers)).status_code == 401


async def test_delete_protects_self_and_allows_other_admin(client, db, admin_headers):
    actor = await db.scalar(select(User).where(User.role == UserRole.ADMIN))
    assert (await client.delete(f"/api/admin/users/{actor.id}", headers=admin_headers)).status_code == 409
    other = await make_user(db, "admin2@example.com", role=UserRole.ADMIN)
    other_headers = headers(other)
    assert (await client.delete(f"/api/admin/users/{other.id}", headers=admin_headers)).status_code == 204
    assert (await client.get("/api/admin/users", headers=other_headers)).status_code == 401
    assert (await client.get("/api/admin/users", headers=admin_headers)).status_code == 200


@pytest.mark.parametrize("published", [False, True])
async def test_admin_enrollment_is_idempotent_and_visible_to_student(client, db, admin_headers, course_factory, published):
    user = await make_user(db)
    course = await course_factory(slug="admin-enrollment", is_published=published)
    path = f"/api/admin/users/{user.id}/courses/{course.id}"
    for _ in range(2):
        response = await client.put(path, headers=admin_headers)
        assert response.status_code == 204 and response.content == b""
    assert await db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.user_id == user.id)) == 1
    detail = (await client.get(f"/api/admin/users/{user.id}", headers=admin_headers)).json()
    assert detail["courses"][0]["enrolled"] is True
    assert detail["courses"][0]["is_published"] is published
    enrolled = await client.get("/api/enrollments/me", headers=headers(user))
    assert enrolled.status_code == 200
    assert [item["course_id"] for item in enrolled.json()] == [course.id]
    options = (await client.get("/api/admin/courses", headers=admin_headers)).json()
    assert options == [{"id": course.id, "title": course.title, "is_published": published}]


async def test_admin_unenrollment_preserves_history_and_other_enrollments(client, db, admin_headers, learning_data, course_factory):
    user, course, _, _ = learning_data
    other = await make_user(db, "other@example.com")
    another_course = await course_factory(slug="another-course")
    db.add_all([
        Enrollment(user_id=other.id, course_id=course.id),
        Enrollment(user_id=user.id, course_id=another_course.id),
    ])
    await db.commit()
    path = f"/api/admin/users/{user.id}/courses/{course.id}"
    before = (await client.get(f"/api/admin/users/{user.id}", headers=admin_headers)).json()
    progress = next(item for item in before["courses"] if item["id"] == course.id)
    for _ in range(2):
        assert (await client.delete(path, headers=admin_headers)).status_code == 204
    after = (await client.get(f"/api/admin/users/{user.id}", headers=admin_headers)).json()
    assert next(item for item in after["courses"] if item["id"] == course.id) == {**progress, "enrolled": False}
    enrolled = (await client.get("/api/enrollments/me", headers=headers(user))).json()
    assert [item["course_id"] for item in enrolled] == [another_course.id]
    assert await db.scalar(select(Enrollment.id).where(Enrollment.user_id == other.id, Enrollment.course_id == course.id))
    assert (await client.put(path, headers=admin_headers)).status_code == 204
    restored = (await client.get(f"/api/admin/users/{user.id}", headers=admin_headers)).json()
    assert next(item for item in restored["courses"] if item["id"] == course.id) == progress


@pytest.mark.parametrize("method,suffix", [("DELETE", ""), ("PUT", "/courses/1"), ("DELETE", "/courses/1")])
async def test_blocked_admin_cannot_manage_users(client, db, admin_headers, method, suffix):
    actor = await db.scalar(select(User).where(User.role == UserRole.ADMIN))
    actor.blocked_at = datetime.now(UTC)
    await db.commit()
    assert (await client.request(method, f"/api/admin/users/999999{suffix}", headers=admin_headers)).status_code == 403


@pytest.mark.parametrize("method,path,code", [
    ("DELETE", "/api/admin/users/999999", 404),
    ("DELETE", "/api/admin/users/0", 422),
    ("DELETE", "/api/admin/users/9999999999", 422),
    ("PUT", "/api/admin/users/999999/courses/1", 404),
    ("DELETE", "/api/admin/users/999999/courses/1", 404),
    ("PUT", "/api/admin/users/1/courses/999999", 404),
    ("DELETE", "/api/admin/users/1/courses/999999", 404),
    ("PUT", "/api/admin/users/1/courses/0", 422),
    ("DELETE", "/api/admin/users/1/courses/9999999999", 422),
])
async def test_user_management_missing_records_and_invalid_ids(client, admin_headers, method, path, code):
    assert (await client.request(method, path, headers=admin_headers)).status_code == code


@pytest.mark.parametrize("path,code", [
    ("/api/admin/users/999999", 404), ("/api/admin/submissions/999999", 404),
    ("/api/admin/users?page=0", 422), ("/api/admin/users?page_size=101", 422),
    ("/api/admin/submissions?status=invalid", 422),
    ("/api/admin/submissions?user_id=9999999999", 422),
    ("/api/admin/users/9999999999", 422),
    ("/api/admin/submissions?date_from=2026-11-03&date_to=2026-11-02", 422),
])
async def test_missing_records_and_bad_filters(client, admin_headers, path, code):
    assert (await client.get(path, headers=admin_headers)).status_code == code


@pytest.mark.parametrize("target", ["lesson", "lesson_short", "step", "absolute"])
async def test_latest_homework_scope_and_history(client, db, admin_headers, learning_data, target, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "frontend_url", "https://academy.example")
    user, course, tasks, attempts = learning_data
    step = await db.get(Step, tasks[1].step_id)
    urls = {
        "lesson": f"/{course.slug}/lessons/{step.lesson_id}/steps",
        "lesson_short": f"/{course.slug}/lessons/{step.lesson_id}",
        "step": f"/{course.slug}/steps/{step.id}?task=7#editor",
        "absolute": f"https://academy.example/{course.slug}/steps/{step.id}",
    }
    response = await client.post(f"/api/admin/users/{user.id}/homework", headers=admin_headers,
                                 json={"title": "Последнее ДЗ", "url": urls[target]})
    assert response.status_code == 201
    # An older assignment and other pupils' solutions must not affect the report.
    db.add(Homework(user_id=user.id, title="Старое", url="/unsupported",
                    created_at=datetime(2020, 1, 1, tzinfo=UTC)))
    other = await make_user(db, "other@example.com")
    db.add(Submission(task_id=tasks[1].id, user_id=other.id, source_code="other",
                      status=SubmissionStatus.ACCEPTED))
    # Marking a task's step complete does not count as an accepted solution.
    db.add(StepProgress(user_id=user.id, step_id=step.id))
    await db.commit()
    response = await client.get(f"/api/admin/users/{user.id}/homework/latest-progress", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["homework"]["title"] == "Последнее ДЗ"
    assert data["unavailable_reason"] is None
    assert data["lesson_title"] == "Урок" and data["course_title"] == "Python"
    whole_lesson = target in {"lesson", "lesson_short"}
    assert data["total_tasks"] == (2 if whole_lesson else 1)
    assert data["solved_tasks"] == (1 if whole_lesson else 0)
    assert [row["position"] for row in data["steps"]] == ([1, 2, 3] if whole_lesson else [2, 3])
    assert [row["status"] for row in data["steps"]] == (["solved", "attempted", "not_started"] if whole_lesson else ["attempted", "not_started"])
    assert data["steps"][-1]["task_id"] is None
    assert data["steps"][0]["url"] == f"/{course.slug}/steps/{tasks[0].step_id if whole_lesson else step.id}?preview=1"
    assert data["submissions"]["total"] == (3 if whole_lesson else 1)
    assert [item["id"] for item in data["submissions"]["items"]] == ([item.id for item in reversed(attempts)] if whole_lesson else [attempts[2].id])
    assert all("source_code" not in item for item in data["submissions"]["items"])


async def test_homework_step_states_and_stable_pagination(client, db, admin_headers, learning_data):
    user, course, tasks, attempts = learning_data
    first = await db.get(Step, tasks[0].step_id)
    theory = await db.scalar(select(Step).where(Step.lesson_id == first.lesson_id, Step.order == 2))
    db.add(StepProgress(user_id=user.id, step_id=theory.id))
    extra = [Step(lesson_id=first.lesson_id, title=f"Дополнительный {i}", order=3, content={}) for i in range(2)]
    db.add_all(extra)
    await db.flush()
    extra_tasks = [Task(step_id=step.id) for step in extra]
    db.add_all(extra_tasks)
    await db.flush()
    # A later wrong answer must not undo an accepted solution.
    for task, status in [(tasks[0], SubmissionStatus.RUNTIME_ERROR), (extra_tasks[1], SubmissionStatus.PENDING)]:
        db.add(Submission(task_id=task.id, user_id=user.id, source_code="pass", status=status,
                          submitted_at=datetime(2026, 11, 4, tzinfo=UTC)))
    db.add(Homework(user_id=user.id, title="ДЗ", url=f"/{course.slug}/steps/{first.id}"))
    await db.commit()
    path = f"/api/admin/users/{user.id}/homework/latest-progress"
    data = (await client.get(path, headers=admin_headers, params={"page_size": 1})).json()
    assert data["total_tasks"] == 4 and data["solved_tasks"] == 1
    assert [row["status"] for row in data["steps"]] == ["solved", "attempted", "completed", "not_started", "checking"]
    assert [row["id"] for row in data["steps"]][-2:] == [step.id for step in extra]
    assert data["submissions"]["total"] == 5
    first_id = data["submissions"]["items"][0]["id"]
    data = (await client.get(path, headers=admin_headers, params={"page_size": 1, "page": 2})).json()
    assert data["submissions"]["page"] == 2
    assert data["submissions"]["items"][0]["id"] < first_id
    assert data["submissions"]["total"] == 5


@pytest.mark.parametrize("url", [
    "/unsupported", "/wrong-course/steps/{step}", "/admin/steps/{step}/task",
    "/admin-python/steps/999999", "/admin-python/steps/999999999999999999999",
    "https://external.example/admin-python/steps/{step}",
])
async def test_unresolvable_homework_is_explicit(client, db, admin_headers, learning_data, url):
    user, _, tasks, _ = learning_data
    db.add(Homework(user_id=user.id, title="ДЗ", url=url.format(step=tasks[0].step_id)))
    await db.commit()
    response = await client.get(f"/api/admin/users/{user.id}/homework/latest-progress", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["homework"]["title"] == "ДЗ" and data["unavailable_reason"]
    assert data["steps"] == [] and data["total_tasks"] == 0
    assert data["submissions"]["total"] == 0


async def test_latest_homework_empty_ties_and_deletion(client, db, admin_headers, learning_data):
    user, course, tasks, _ = learning_data
    path = f"/api/admin/users/{user.id}/homework/latest-progress"
    assert (await client.get(path, headers=admin_headers)).json()["homework"] is None
    timestamp = datetime(2026, 11, 22, tzinfo=UTC)
    homework = [Homework(user_id=user.id, title=f"ДЗ {i}", url=f"/{course.slug}/steps/{task.step_id}",
                         created_at=timestamp) for i, task in enumerate(tasks)]
    db.add_all(homework)
    await db.commit()
    assert (await client.get(path, headers=admin_headers)).json()["homework"]["id"] == homework[1].id
    assert (await client.delete(f"/api/admin/users/{user.id}/homework/{homework[1].id}", headers=admin_headers)).status_code == 204
    assert (await client.get(path, headers=admin_headers)).json()["homework"]["id"] == homework[0].id
    for suffix in ("?page=0", "?page_size=101"):
        assert (await client.get(path + suffix, headers=admin_headers)).status_code == 422
    assert (await client.get("/api/admin/users/999999/homework/latest-progress", headers=admin_headers)).status_code == 404
    admin_id = (await client.get("/api/users/me", headers=admin_headers)).json()["id"]
    assert (await client.get(f"/api/admin/users/{admin_id}/homework/latest-progress", headers=admin_headers)).status_code == 404


async def test_admin_opens_task_viewer_without_enrollment_or_progress_changes(client, db, admin_headers, learning_data):
    user, course, tasks, _ = learning_data
    step = await db.get(Step, tasks[0].step_id)
    step.content = {"version": 1, "layout": "vertical", "blocks": []}
    await db.commit()
    path = f"/api/steps/{tasks[0].step_id}/viewer/admin"
    params = {"course_slug": course.slug}
    response = await client.get(path, params=params, headers=admin_headers)
    assert response.status_code == 200  # Also supports a draft course.
    data = response.json()
    assert data["step"]["id"] == tasks[0].step_id
    assert len(data["lesson"]["steps"]) == 3
    assert (await client.get(path, params={"course_slug": "wrong"}, headers=admin_headers)).status_code == 404
    assert (await client.get(path, params=params, headers=headers(user))).status_code == 403
    admin_id = (await client.get("/api/users/me", headers=admin_headers)).json()["id"]
    for model in (Enrollment, CourseActivity, StepProgress, Submission):
        assert await db.scalar(select(func.count()).select_from(model).where(model.user_id == admin_id)) == 0
    task = await client.get(f"/api/tasks/admin/by-step/{tasks[0].step_id}", headers=admin_headers)
    assert task.status_code == 200 and task.json()["id"] == tasks[0].id
    # The normal student viewer still enforces publication and enrollment.
    normal = f"/api/steps/{tasks[0].step_id}/viewer"
    assert (await client.get(normal, params=params, headers=headers(user))).status_code == 404
    course.is_published = True
    await db.commit()
    assert (await client.get(path, params=params, headers=admin_headers)).status_code == 200
    assert (await client.get(normal, params=params, headers=admin_headers)).status_code == 403
