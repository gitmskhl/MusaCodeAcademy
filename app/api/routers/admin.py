from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.dependencies import DBSession, OnlyAdmin, require_role
from app.enums import SubmissionStatus, UserRole
from app.models import Course
from app.schemas.admin import (
    AdminCourseOption, AdminSubmissionDetail, AdminSubmissionPage,
    AdminUser, AdminUserDetail, AdminUserPage, UserBlockUpdate, UserAIAssistanceUpdate,
)
from app.services import admin as service
from app.services.database_backup import DatabaseBackupResponse, create_database_backup
from app.core.config import settings

router = APIRouter(dependencies=[Depends(require_role(UserRole.ADMIN))])
Page = Annotated[int, Query(ge=1, le=1_000_000)]
PageSize = Annotated[int, Query(ge=1, le=100)]
OptionalId = Annotated[int | None, Query(gt=0, le=2_147_483_647)]
RecordId = Annotated[int, Path(gt=0, le=2_147_483_647)]
Search = Annotated[str | None, Query(max_length=255)]


@router.post("/database/export", response_class=FileResponse)
async def export_database():
    path = await create_database_backup()
    return DatabaseBackupResponse(
        path, filename=path.name, media_type="application/octet-stream",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/courses", response_model=list[AdminCourseOption])
async def admin_courses(db: DBSession):
    return (await db.execute(select(Course.id, Course.title, Course.is_published)
                             .order_by(Course.title, Course.id))).mappings().all()


@router.get("/ai-models", response_model=list[str])
async def admin_ai_models():
    return settings.available_ai_models()


@router.get("/users", response_model=AdminUserPage)
async def admin_users(db: DBSession, q: Search = None, role: UserRole | None = None,
                      blocked: bool | None = None, course_id: OptionalId = None,
                      page: Page = 1, page_size: PageSize = 25):
    return await service.list_users(db, q=q, role=role, blocked=blocked, course_id=course_id, page=page, page_size=page_size)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def admin_user_detail(user_id: RecordId, db: DBSession):
    return await service.get_user(db, user_id)


@router.patch("/users/{user_id}/block", response_model=AdminUser)
async def admin_user_block(user_id: RecordId, update: UserBlockUpdate, actor: OnlyAdmin, db: DBSession):
    return await service.set_user_block(db, user_id=user_id, actor_id=actor.id, update=update)


@router.delete("/users/{user_id}", status_code=204)
async def admin_user_delete(user_id: RecordId, actor: OnlyAdmin, db: DBSession):
    await service.delete_user(db, user_id=user_id, actor_id=actor.id)
    return Response(status_code=204)


@router.put("/users/{user_id}/courses/{course_id}", status_code=204)
async def admin_user_enroll(user_id: RecordId, course_id: RecordId, actor: OnlyAdmin, db: DBSession):
    await service.set_user_enrollment(db, user_id=user_id, course_id=course_id, actor_id=actor.id, enrolled=True)
    return Response(status_code=204)


@router.delete("/users/{user_id}/courses/{course_id}", status_code=204)
async def admin_user_unenroll(user_id: RecordId, course_id: RecordId, actor: OnlyAdmin, db: DBSession):
    await service.set_user_enrollment(db, user_id=user_id, course_id=course_id, actor_id=actor.id, enrolled=False)
    return Response(status_code=204)


@router.patch("/users/{user_id}/ai-assistance", response_model=AdminUser)
async def admin_user_ai_assistance(user_id: RecordId, update: UserAIAssistanceUpdate, db: DBSession):
    return await service.set_user_ai_assistance(db, user_id=user_id, update=update)


@router.get("/submissions", response_model=AdminSubmissionPage)
async def admin_submissions(db: DBSession, q: Search = None, user_id: OptionalId = None,
                            course_id: OptionalId = None, task_id: OptionalId = None,
                            status: SubmissionStatus | None = None,
                            date_from: date | None = None, date_to: date | None = Query(default=None, le=date(9999, 12, 30)),
                            page: Page = 1, page_size: PageSize = 25):
    return await service.list_submissions(db, q=q, user_id=user_id, course_id=course_id, task_id=task_id,
                                          status=status, date_from=date_from, date_to=date_to, page=page, page_size=page_size)


@router.get("/submissions/{submission_id}", response_model=AdminSubmissionDetail)
async def admin_submission_detail(submission_id: RecordId, db: DBSession):
    return await service.get_submission(db, submission_id)
