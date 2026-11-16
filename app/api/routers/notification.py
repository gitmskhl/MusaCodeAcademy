from typing import Annotated

from fastapi import APIRouter, Path, Query, Response

from app.api.dependencies import CurrentUser, DBSession
from app.schemas.notification import HomeworkPage, NotificationPage, NotificationRead
from app.services import notification as service

router = APIRouter()
Page = Annotated[int, Query(ge=1, le=1_000_000)]
PageSize = Annotated[int, Query(ge=1, le=100)]
RecordId = Annotated[int, Path(gt=0, le=2_147_483_647)]


@router.get("/notifications", response_model=NotificationPage)
async def notifications(db: DBSession, user: CurrentUser, page: Page = 1, page_size: PageSize = 20):
    return await service.list_notifications(db, user_id=user.id, page=page, page_size=page_size)


@router.post("/notifications/read-all", status_code=204)
async def read_all_notifications(db: DBSession, user: CurrentUser):
    await service.mark_all_read(db, user_id=user.id)
    return Response(status_code=204)


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead)
async def read_notification(notification_id: RecordId, db: DBSession, user: CurrentUser):
    return await service.mark_read(db, user_id=user.id, notification_id=notification_id)


@router.get("/homework", response_model=HomeworkPage)
async def my_homework(db: DBSession, user: CurrentUser, page: Page = 1, page_size: PageSize = 20):
    return await service.list_homework(db, user_id=user.id, page=page, page_size=page_size)


@router.post("/homework/{homework_id}/read-notification", status_code=204)
async def read_homework_notification(homework_id: RecordId, db: DBSession, user: CurrentUser):
    await service.read_homework_notification(db, user_id=user.id, homework_id=homework_id)
    return Response(status_code=204)
