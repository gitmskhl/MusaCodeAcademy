from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import UserRole
from app.models import Homework, Notification, User
from app.schemas.notification import HomeworkCreate, NotificationCreate, RecipientSelection


def _recipients(selection: RecipientSelection):
    query = select(User.id).where(User.role == UserRole.STUDENT)
    if selection.recipient_mode == "selected":
        query = query.where(User.id.in_(selection.recipient_ids))
    return query


async def recipient_count(db: AsyncSession, selection: RecipientSelection) -> int:
    count = await db.scalar(select(func.count()).select_from(_recipients(selection).subquery()))
    if selection.recipient_mode == "selected" and count != len(selection.recipient_ids):
        raise HTTPException(422, "Некоторые получатели не найдены или не являются учениками")
    return count


async def search_students(db: AsyncSession, *, q: str, page: int, page_size: int):
    query = select(User).where(User.role == UserRole.STUDENT)
    if q.strip():
        term = q.strip()
        query = query.where(or_(User.email.icontains(term, autoescape=True),
                               (User.first_name + " " + User.last_name).icontains(term, autoescape=True)))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    items = (await db.scalars(query.order_by(User.last_name, User.first_name, User.id)
                             .offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def send_notification(db: AsyncSession, data: NotificationCreate) -> int:
    # Lock recipients until delivery so deleting an account cannot partially
    # deliver a selected mailing or break its foreign keys.
    ids = (await db.scalars(_recipients(data).order_by(User.id).with_for_update(read=True))).all()
    if data.recipient_mode == "selected" and len(ids) != len(data.recipient_ids):
        raise HTTPException(422, "Некоторые получатели не найдены или не являются учениками")
    if not ids:
        raise HTTPException(422, "Нет учеников для отправки")
    now = datetime.now(UTC)
    try:
        for start in range(0, len(ids), 500):
            await db.execute(insert(Notification), [
                {"user_id": user_id, "title": data.title, "text": data.text, "created_at": now}
                for user_id in ids[start:start + 500]
            ])
        await db.commit()
    except BaseException:
        await db.rollback()
        raise
    return len(ids)


async def require_student(db: AsyncSession, user_id: int, *, lock=False):
    query = select(User.id).where(User.id == user_id, User.role == UserRole.STUDENT)
    if lock:
        query = query.with_for_update(read=True)
    if await db.scalar(query) is None:
        raise HTTPException(404, "Ученик не найден")


async def assign_homework(db: AsyncSession, *, user_id: int, actor_id: int, data: HomeworkCreate):
    await require_student(db, user_id, lock=True)
    homework = Homework(user_id=user_id, assigned_by_id=actor_id, **data.model_dump())
    try:
        db.add(homework)
        await db.flush()
        db.add(Notification(user_id=user_id, title=homework.title, text=homework.comment or "",
                            homework_id=homework.id))
        await db.commit()
    except BaseException:
        await db.rollback()
        raise
    return homework


async def delete_homework(db: AsyncSession, *, user_id: int, homework_id: int):
    await require_student(db, user_id)
    deleted_id = await db.scalar(delete(Homework).where(
        Homework.id == homework_id, Homework.user_id == user_id,
    ).returning(Homework.id))
    if deleted_id is None:
        raise HTTPException(404, "Домашнее задание не найдено")
    # The homework foreign key also removes its notification, including unread
    # counts, in the same transaction. Other assignments are unaffected.
    await db.commit()


async def list_homework(db: AsyncSession, *, user_id: int, page: int, page_size: int):
    query = select(Homework).where(Homework.user_id == user_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    items = (await db.scalars(query.order_by(Homework.created_at.desc(), Homework.id.desc())
                             .offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def list_notifications(db: AsyncSession, *, user_id: int, page: int, page_size: int):
    query = select(Notification).where(Notification.user_id == user_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    unread = await db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id == user_id, Notification.read_at.is_(None)))
    items = (await db.scalars(query.options(selectinload(Notification.homework))
                             .order_by(Notification.created_at.desc(), Notification.id.desc())
                             .offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": items, "total": total, "unread_count": unread, "page": page, "page_size": page_size}


async def mark_read(db: AsyncSession, *, user_id: int, notification_id: int):
    query = select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    notification = await db.scalar(query.options(selectinload(Notification.homework)))
    if notification is None:
        raise HTTPException(404, "Уведомление не найдено")
    # Conditional update preserves the first read time even for concurrent clicks.
    await db.execute(update(Notification).where(Notification.id == notification_id, Notification.user_id == user_id,
                                                Notification.read_at.is_(None))
                     .values(read_at=datetime.now(UTC)))
    await db.commit()
    await db.refresh(notification, attribute_names=["read_at"])
    return notification


async def mark_all_read(db: AsyncSession, *, user_id: int):
    await db.execute(update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
                     .values(read_at=datetime.now(UTC)))
    await db.commit()


async def read_homework_notification(db: AsyncSession, *, user_id: int, homework_id: int):
    if await db.scalar(select(Homework.id).where(Homework.id == homework_id, Homework.user_id == user_id)) is None:
        raise HTTPException(404, "Домашнее задание не найдено")
    await db.execute(update(Notification).where(Notification.user_id == user_id,
                                               Notification.homework_id == homework_id,
                                               Notification.read_at.is_(None))
                     .values(read_at=datetime.now(UTC)))
    await db.commit()
