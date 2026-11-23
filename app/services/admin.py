"""Administrative user management and monitoring."""
from datetime import UTC, datetime, time, timedelta
import re
from urllib.parse import quote, unquote, urlsplit

from fastapi import HTTPException
from sqlalchemy import case, delete, distinct, func, or_, select, true, union_all
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import SubmissionStatus, UserRole
from app.models import Course, CourseActivity, Enrollment, Homework, Lesson, Section, Step, StepProgress, Submission, Task, User
from app.schemas.admin import AdminUser, UserBlockUpdate, UserAIAssistanceUpdate
from app.core.config import settings
from app.services.ai_hint import AI_USER_LOCK_NAMESPACE
from app.services.notification import require_student


def _latest_activity(*values: datetime | None) -> datetime | None:
    # Legacy timestamp-without-time-zone columns contain UTC values. Normalize
    # them before comparing with the aware timestamps used by newer tables.
    return max((
        value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        for value in values if value is not None
    ), default=None)


def _step_courses():
    return (
        select(Step.id.label("step_id"), Section.course_id)
        .join(Lesson, Lesson.id == Step.lesson_id)
        .join(Section, Section.id == Lesson.section_id)
        .subquery()
    )


def _user_summary():
    attempts = (
        select(
            Submission.user_id,
            func.count().label("submissions_count"),
            func.count(distinct(case(
                (Submission.status == SubmissionStatus.ACCEPTED, Submission.task_id)
            ))).label("solved_tasks_count"),
        ).group_by(Submission.user_id).subquery()
    )
    events = union_all(
        select(Submission.user_id, Submission.submitted_at.label("at")),
        select(CourseActivity.user_id, CourseActivity.last_visited_at.label("at")),
        select(StepProgress.user_id, StepProgress.completed_at.label("at")),
    ).subquery()
    activity = select(events.c.user_id, func.max(events.c.at).label("last_activity_at")).group_by(events.c.user_id).subquery()
    latest_homework = (
        select(Homework.id, Homework.due_date)
        .where(Homework.user_id == User.id)
        .order_by(Homework.created_at.desc(), Homework.id.desc())
        .limit(1).correlate(User).lateral()
    )
    return (
        select(
            User,
            func.coalesce(attempts.c.submissions_count, 0).label("submissions_count"),
            func.coalesce(attempts.c.solved_tasks_count, 0).label("solved_tasks_count"),
            activity.c.last_activity_at,
            latest_homework.c.id.label("latest_homework_id"),
            latest_homework.c.due_date.label("latest_homework_due_date"),
        )
        .outerjoin(attempts, attempts.c.user_id == User.id)
        .outerjoin(activity, activity.c.user_id == User.id)
        .outerjoin(latest_homework, true())
    )


def _user_dict(row):
    return {
        **AdminUser.model_validate(row.User).model_dump(),
        "submissions_count": row.submissions_count,
        "solved_tasks_count": row.solved_tasks_count,
        "last_activity_at": row.last_activity_at,
        "latest_homework": {
            "id": row.latest_homework_id,
            "due_date": row.latest_homework_due_date,
        } if row.latest_homework_id is not None else None,
    }


def _user_search(q: str):
    conditions = [
        User.email.icontains(q, autoescape=True),
        (User.first_name + " " + User.last_name).icontains(q, autoescape=True),
    ]
    if q.isascii() and q.isdecimal() and len(q) <= 10 and int(q) <= 2_147_483_647:
        conditions.append(User.id == int(q))
    return or_(*conditions)


async def list_users(db: AsyncSession, *, q, role, blocked, course_id, page, page_size,
                     sort_by="created_at", sort_order="desc"):
    query = _user_summary()
    if q:
        query = query.where(_user_search(q.strip()))
    if role is not None:
        query = query.where(User.role == role)
    if blocked is not None:
        query = query.where(User.blocked_at.is_not(None) if blocked else User.blocked_at.is_(None))
    if course_id is not None:
        query = query.where(select(Enrollment.id).where(
            Enrollment.user_id == User.id, Enrollment.course_id == course_id
        ).exists())
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_column = {
        "id": User.id,
        "created_at": User.created_at,
        "last_activity_at": query.selected_columns.last_activity_at,
    }[sort_by]
    ascending = sort_order == "asc"
    order = sort_column.asc() if ascending else sort_column.desc()
    # Keep users without activity last in either direction, and break ties by ID
    # so users with equal timestamps cannot move between pages.
    rows = (await db.execute(query.order_by(order.nulls_last(), User.id.asc() if ascending else User.id.desc())
                             .offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": [_user_dict(row) for row in rows], "total": total, "page": page, "page_size": page_size}


async def get_user(db: AsyncSession, user_id: int):
    row = (await db.execute(_user_summary().where(User.id == user_id))).one_or_none()
    if row is None:
        raise HTTPException(404, "Пользователь не найден")

    step_courses = _step_courses()
    steps = (
        select(
            step_courses.c.course_id,
            func.count(distinct(step_courses.c.step_id)).label("total_steps"),
            func.count(distinct(StepProgress.step_id)).label("completed_steps"),
            func.count(distinct(Task.id)).label("total_tasks"),
            func.max(StepProgress.completed_at).label("completed_at"),
        )
        .outerjoin(StepProgress, (StepProgress.step_id == step_courses.c.step_id) & (StepProgress.user_id == user_id))
        .outerjoin(Task, Task.step_id == step_courses.c.step_id)
        .group_by(step_courses.c.course_id).subquery()
    )
    attempts = (
        select(
            step_courses.c.course_id,
            func.count().label("submissions_count"),
            func.count(distinct(case(
                (Submission.status == SubmissionStatus.ACCEPTED, Submission.task_id)
            ))).label("solved_tasks"),
            func.max(Submission.submitted_at).label("submitted_at"),
        ).select_from(Submission)
        .join(Task, Task.id == Submission.task_id)
        .join(step_courses, step_courses.c.step_id == Task.step_id)
        .where(Submission.user_id == user_id)
        .group_by(step_courses.c.course_id).subquery()
    )
    courses = (await db.execute(
        select(
            Course.id, Course.title, Course.is_published,
            Enrollment.id.label("enrollment_id"),
            steps.c.total_steps, steps.c.completed_steps, steps.c.total_tasks, steps.c.completed_at,
            attempts.c.submissions_count, attempts.c.solved_tasks, attempts.c.submitted_at,
            CourseActivity.last_visited_at,
        ).outerjoin(Enrollment, (Enrollment.course_id == Course.id) & (Enrollment.user_id == user_id))
        .outerjoin(steps, steps.c.course_id == Course.id)
        .outerjoin(attempts, attempts.c.course_id == Course.id)
        .outerjoin(CourseActivity, (CourseActivity.course_id == Course.id) & (CourseActivity.user_id == user_id))
        .where(or_(Enrollment.id.is_not(None), attempts.c.submissions_count.is_not(None),
                   steps.c.completed_steps > 0, CourseActivity.id.is_not(None)))
        .order_by(Course.title, Course.id)
    )).all()
    return {**_user_dict(row), "courses": [
        {
            "id": course.id, "title": course.title, "is_published": course.is_published,
            "enrolled": course.enrollment_id is not None,
            **{key: getattr(course, key) or 0 for key in (
                "total_steps", "completed_steps", "total_tasks", "submissions_count", "solved_tasks"
            )},
            "last_activity_at": _latest_activity(
                course.completed_at, course.submitted_at, course.last_visited_at
            ),
        } for course in courses
    ]}


async def set_user_ai_assistance(db: AsyncSession, *, user_id: int, update: UserAIAssistanceUpdate):
    try:
        if not await db.scalar(select(func.pg_try_advisory_xact_lock(AI_USER_LOCK_NAMESPACE, user_id))):
            raise HTTPException(409, "Подсказка пользователя ещё готовится. Сохраните настройки после её завершения.")
        target = await db.get(User, user_id, populate_existing=True)
        if target is None:
            raise HTTPException(404, "Пользователь не найден")
        if any(getattr(update, key) is None for key in update.model_fields_set - {"enabled"}):
            raise HTTPException(422, "Лимиты не могут быть пустыми.")
        daily_limit = update.daily_limit if update.daily_limit is not None else target.ai_daily_limit
        allocations = update.model_limits if update.model_limits is not None else target.ai_model_limits
        if {"daily_limit", "model_limits"} & update.model_fields_set:
            if allocations is None:
                available = settings.available_ai_models()
                allocations = {available[0]: daily_limit} if available else {}
            if not allocations or sum(allocations.values()) != daily_limit:
                raise HTTPException(422, "Сумма запросов по моделям должна совпадать с дневным лимитом.")
            if set(allocations) - set(settings.available_ai_models()):
                raise HTTPException(422, "Можно выбрать только модели, перечисленные в AI_MODEL_X в .env.")
            target.ai_daily_limit = daily_limit
            target.ai_model_limits = allocations
        target.ai_assistance_enabled = update.enabled
        target.updated_at = datetime.now(UTC)
        await db.commit()
        return target
    except BaseException:
        await db.rollback()
        raise


async def _lock_user_for_admin_change(db: AsyncSession, *, user_id: int, actor_id: int) -> User:
    # Serialize account changes, including simultaneous attempts by two admins
    # to block or delete one another. Recheck the actor after acquiring locks.
    users = (await db.scalars(select(User).where(or_(
        User.role == UserRole.ADMIN, User.id == user_id
    )).order_by(User.id).with_for_update().execution_options(populate_existing=True))).all()
    actor = next((user for user in users if user.id == actor_id), None)
    if actor is None or actor.blocked_at is not None or actor.role != UserRole.ADMIN:
        raise HTTPException(403, "Доступ администратора недоступен")
    target = next((user for user in users if user.id == user_id), None)
    if target is None:
        raise HTTPException(404, "Пользователь не найден")
    return target


async def delete_user(db: AsyncSession, *, user_id: int, actor_id: int) -> None:
    target = await _lock_user_for_admin_change(db, user_id=user_id, actor_id=actor_id)
    if target.id == actor_id:
        raise HTTPException(409, "Нельзя удалить собственный аккаунт")
    # The ORM removes password reset tokens (their FK has no ON DELETE).
    # Database cascades remove submissions, progress, activity and AI quotas.
    await db.delete(target)
    await db.commit()


async def set_user_enrollment(db: AsyncSession, *, user_id: int, course_id: int,
                              actor_id: int, enrolled: bool) -> None:
    await _lock_user_for_admin_change(db, user_id=user_id, actor_id=actor_id)
    course = await db.scalar(select(Course.id).where(Course.id == course_id)
                             .with_for_update(read=True, key_share=True))
    if course is None:
        raise HTTPException(404, "Курс не найден")
    if enrolled:
        # Admins can enroll users in drafts as well as published courses.
        # Upsert also handles a simultaneous student self-enrollment.
        await db.execute(insert(Enrollment).values(user_id=user_id, course_id=course_id)
                         .on_conflict_do_nothing(index_elements=[Enrollment.user_id, Enrollment.course_id]))
    else:
        await db.execute(delete(Enrollment).where(
            Enrollment.user_id == user_id, Enrollment.course_id == course_id
        ))
    await db.commit()


async def set_user_block(db: AsyncSession, *, user_id: int, actor_id: int, update: UserBlockUpdate):
    target = await _lock_user_for_admin_change(db, user_id=user_id, actor_id=actor_id)
    if target.id == actor_id:
        raise HTTPException(409, "Нельзя изменить блокировку собственного аккаунта")
    reason = (update.reason or "").strip()
    if update.blocked and not reason:
        raise HTTPException(422, "Укажите причину блокировки")
    if update.blocked:
        if target.blocked_at is None:
            target.blocked_at = datetime.now(UTC)
        target.block_reason = reason
    else:
        target.blocked_at = None
        target.block_reason = None
    target.updated_at = datetime.now(UTC)
    await db.commit()
    return target


def _submissions(*, detail=False):
    columns = [
        Submission.id, Submission.user_id,
        (User.first_name + " " + User.last_name).label("user_name"), User.email.label("user_email"),
        Submission.task_id, Step.id.label("step_id"), Step.title.label("step_title"),
        Lesson.title.label("lesson_title"), Course.id.label("course_id"), Course.title.label("course_title"),
        Course.slug.label("course_slug"),
        Submission.status, Submission.submitted_at, Submission.passed_tests, Submission.total_tests,
    ]
    if detail:
        columns += [Submission.source_code, Submission.failed_test_id, Submission.actual_output, Submission.ai_hint, Submission.ai_hint_model]
    return (select(*columns).select_from(Submission)
            .join(User, User.id == Submission.user_id).join(Task, Task.id == Submission.task_id)
            .join(Step, Step.id == Task.step_id).join(Lesson, Lesson.id == Step.lesson_id)
            .join(Section, Section.id == Lesson.section_id).join(Course, Course.id == Section.course_id))


async def list_submissions(db: AsyncSession, *, q, user_id, course_id, task_id, status, date_from, date_to, page, page_size):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "Начальная дата должна быть не позже конечной")
    query = _submissions()
    if q:
        query = query.where(_user_search(q.strip()))
    for column, value in ((Submission.user_id, user_id), (Course.id, course_id),
                          (Submission.task_id, task_id), (Submission.status, status)):
        if value is not None:
            query = query.where(column == value)
    if date_from:
        query = query.where(Submission.submitted_at >= datetime.combine(date_from, time.min, UTC))
    if date_to:
        query = query.where(Submission.submitted_at < datetime.combine(date_to + timedelta(days=1), time.min, UTC))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await db.execute(query.order_by(Submission.submitted_at.desc(), Submission.id.desc())
                             .offset((page - 1) * page_size).limit(page_size))).mappings().all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


async def get_submission(db: AsyncSession, submission_id: int):
    row = (await db.execute(_submissions(detail=True).where(Submission.id == submission_id))).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, "Отправка не найдена")
    return row


def _homework_target(url: str):
    """Recognize platform links without fetching any supplied URL."""
    try:
        parsed = urlsplit(url)
        if parsed.netloc:
            platform = urlsplit(settings.frontend_url)
            if (parsed.hostname, parsed.port) != (platform.hostname, platform.port):
                return None
        path = unquote(parsed.path).rstrip("/")
    except ValueError:
        return None
    match = re.fullmatch(r"/([^/]+)/(steps|lessons)/([0-9]+)(/steps)?", path)
    if not match:
        return None
    slug, kind, record_id, suffix = match.groups()
    if (kind == "steps" and suffix) or len(record_id) > 10 or not 0 < int(record_id) <= 2_147_483_647:
        return None
    return slug.lower(), kind, int(record_id)


async def latest_homework_progress(db: AsyncSession, *, user_id: int, page: int, page_size: int):
    await require_student(db, user_id)
    homework = await db.scalar(select(Homework).where(Homework.user_id == user_id)
                               .order_by(Homework.created_at.desc(), Homework.id.desc()).limit(1))
    report = {
        "homework": homework,
        "submissions": {"items": [], "total": 0, "page": page, "page_size": page_size},
    }
    if homework is None:
        return report
    target = _homework_target(homework.url)
    if target is None:
        return {**report, "unavailable_reason": "Статистика доступна для ссылок на урок или степ этой платформы."}
    slug, kind, record_id = target
    query = (select(Lesson.id, Lesson.title, Course.slug, Course.title.label("course_title"))
             .join(Section, Section.id == Lesson.section_id)
             .join(Course, Course.id == Section.course_id).where(Course.slug == slug))
    if kind == "steps":
        query = query.join(Step, Step.lesson_id == Lesson.id).where(Step.id == record_id)
    else:
        query = query.where(Lesson.id == record_id)
    lesson = (await db.execute(query)).one_or_none()
    if lesson is None:
        return {**report, "unavailable_reason": "Урок или степ по ссылке не найден. Возможно, он удалён или ссылка изменилась."}

    rows = (await db.execute(
        select(Step.id, Step.title, Task.id.label("task_id"), StepProgress.id.label("progress_id"))
        .outerjoin(Task, Task.step_id == Step.id)
        .outerjoin(StepProgress, (StepProgress.step_id == Step.id) & (StepProgress.user_id == user_id))
        .where(Step.lesson_id == lesson.id).order_by(Step.order, Step.id)
    )).all()
    # Slice the same deterministic order as the lesson viewer, including ties.
    start = next((index for index, row in enumerate(rows) if row.id == record_id), 0) if kind == "steps" else 0
    scope = rows[start:]
    task_ids = [row.task_id for row in scope if row.task_id is not None]
    attempts = (select(Submission).where(Submission.user_id == user_id, Submission.task_id.in_(task_ids))
                .subquery())
    summaries = (await db.execute(
        select(attempts.c.task_id, func.count().label("submissions_count"),
               func.bool_or(attempts.c.status == SubmissionStatus.ACCEPTED).label("solved"))
        .group_by(attempts.c.task_id)
    )).all()
    summary_by_task = {row.task_id: row for row in summaries}
    latest_statuses = dict((await db.execute(
        select(Submission.task_id, Submission.status)
        .where(Submission.user_id == user_id, Submission.task_id.in_(task_ids))
        .distinct(Submission.task_id)
        .order_by(Submission.task_id, Submission.submitted_at.desc(), Submission.id.desc())
    )).all())
    steps = []
    for position, row in enumerate(scope, start=start + 1):
        summary = summary_by_task.get(row.task_id)
        if row.task_id is None:
            status = "completed" if row.progress_id is not None else "not_started"
        elif summary is not None and summary.solved:
            status = "solved"
        elif latest_statuses.get(row.task_id) in {SubmissionStatus.PENDING, SubmissionStatus.RUNNING}:
            status = "checking"
        else:
            status = "attempted" if summary is not None else "not_started"
        steps.append({
            "id": row.id, "title": row.title, "position": position,
            "url": f"/{quote(lesson.slug, safe='')}/steps/{row.id}?preview=1",
            "task_id": row.task_id, "status": status,
            "submissions_count": summary.submissions_count if summary is not None else 0,
        })
    query = _submissions().where(Submission.user_id == user_id, Submission.task_id.in_(task_ids))
    items = (await db.execute(query.order_by(Submission.submitted_at.desc(), Submission.id.desc())
                              .offset((page - 1) * page_size).limit(page_size))).mappings().all()
    return {
        **report, "course_title": lesson.course_title, "lesson_title": lesson.title,
        "steps": steps, "total_tasks": len(task_ids),
        "solved_tasks": sum(step["status"] == "solved" for step in steps),
        "submissions": {"items": items, "total": sum(row.submissions_count for row in summaries),
                        "page": page, "page_size": page_size},
    }
