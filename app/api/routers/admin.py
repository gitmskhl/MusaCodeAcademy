from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select

from app.api.dependencies import DBSession, OnlyAdmin, require_role
from app.enums import SubmissionStatus, UserRole
from app.models import Course
from app.schemas.admin import (
    AdminCourseOption, AdminSubmissionDetail, AdminSubmissionPage,
    AdminUser, AdminUserDetail, AdminUserPage, UserBlockUpdate,
)
from app.services import admin as service

router = APIRouter(dependencies=[Depends(require_role(UserRole.ADMIN))])
Page = Annotated[int, Query(ge=1, le=1_000_000)]
PageSize = Annotated[int, Query(ge=1, le=100)]
OptionalId = Annotated[int | None, Query(gt=0, le=2_147_483_647)]
RecordId = Annotated[int, Path(gt=0, le=2_147_483_647)]
Search = Annotated[str | None, Query(max_length=255)]


@router.get("/courses", response_model=list[AdminCourseOption])
async def admin_courses(db: DBSession):
    return (await db.execute(select(Course.id, Course.title).order_by(Course.title, Course.id))).mappings().all()


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
