"""Administrative reads stay separate from student enrollment checks."""
from datetime import UTC, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import case, distinct, func, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import SubmissionStatus, UserRole
from app.models import Course, CourseActivity, Enrollment, Lesson, Section, Step, StepProgress, Submission, Task, User
from app.schemas.admin import AdminUser, UserBlockUpdate


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
    return (
        select(
            User,
            func.coalesce(attempts.c.submissions_count, 0).label("submissions_count"),
            func.coalesce(attempts.c.solved_tasks_count, 0).label("solved_tasks_count"),
            activity.c.last_activity_at,
        )
        .outerjoin(attempts, attempts.c.user_id == User.id)
        .outerjoin(activity, activity.c.user_id == User.id)
    )


def _user_dict(row):
    return {
        **AdminUser.model_validate(row.User).model_dump(),
        "submissions_count": row.submissions_count,
        "solved_tasks_count": row.solved_tasks_count,
        "last_activity_at": row.last_activity_at,
    }


def _user_search(q: str):
    conditions = [
        User.email.icontains(q, autoescape=True),
        (User.first_name + " " + User.last_name).icontains(q, autoescape=True),
    ]
    if q.isascii() and q.isdecimal() and len(q) <= 10 and int(q) <= 2_147_483_647:
        conditions.append(User.id == int(q))
    return or_(*conditions)


async def list_users(db: AsyncSession, *, q, role, blocked, course_id, page, page_size):
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
    rows = (await db.execute(query.order_by(User.created_at.desc(), User.id.desc())
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


async def set_user_block(db: AsyncSession, *, user_id: int, actor_id: int, update: UserBlockUpdate):
    # Serialize account changes, including simultaneous attempts by two admins
    # to block one another. Recheck the actor after acquiring the locks.
    users = (await db.scalars(select(User).where(or_(
        User.role == UserRole.ADMIN, User.id == user_id
    )).order_by(User.id).with_for_update().execution_options(populate_existing=True))).all()
    actor = next((user for user in users if user.id == actor_id), None)
    if actor is None or actor.blocked_at is not None or actor.role != UserRole.ADMIN:
        raise HTTPException(403, "Доступ администратора недоступен")
    target = next((user for user in users if user.id == user_id), None)
    if target is None:
        raise HTTPException(404, "Пользователь не найден")
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
        Submission.status, Submission.submitted_at, Submission.passed_tests, Submission.total_tests,
    ]
    if detail:
        columns += [Submission.source_code, Submission.failed_test_id, Submission.actual_output]
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
