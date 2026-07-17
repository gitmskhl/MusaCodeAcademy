from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from app.core.database import get_db
from app.core.security import (
    verify_access_token, oauth2_scheme
)
from app.core.exceptions import InvalidTokenError
from app import models
from app.enums import UserRole

DBSession = Annotated[AsyncSession, Depends(get_db)]

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DBSession
) -> models.User:
    try:
        user_id = verify_access_token(token)
        result = await db.execute(
            select(models.User)
                .where(models.User.id == user_id)
        )
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return user
    
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

CurrentUser = Annotated[models.User, Depends(get_current_user)]

def require_role(*allowed_roles: UserRole):
    async def dependency(current_user: CurrentUser) -> models.User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user
    
    return dependency


OnlyAdmin = Annotated[models.User, Depends(require_role(UserRole.ADMIN))]


async def require_course_enrollment(
    course_id: int,
    current_user: models.User,
    db: AsyncSession,
) -> None:
    enrollment_id = await db.scalar(
        select(models.Enrollment.id)
            .where(
                models.Enrollment.course_id == course_id,
                models.Enrollment.user_id == current_user.id
            )
    )
    if enrollment_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Enrollment required"
        )


async def require_step_enrollment(
    step_id: int,
    current_user: CurrentUser,
    db: DBSession
) -> models.User:
    result = await db.execute(
        select(models.Course.id)
            .join(models.Section, models.Section.course_id == models.Course.id)
            .join(models.Lesson, models.Lesson.section_id == models.Section.id)
            .join(models.Step, models.Step.lesson_id == models.Lesson.id)
            .where(
                models.Step.id == step_id,
                models.Course.is_published.is_(True)
            )
    )
    course_id = result.scalar_one_or_none()
    if course_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    await require_course_enrollment(course_id, current_user, db)
    return current_user


async def require_step_viewer_enrollment(
    step_id: int,
    course_slug: str,
    current_user: CurrentUser,
    db: DBSession
) -> models.User:
    result = await db.execute(
        select(models.Course.id)
            .join(models.Section, models.Section.course_id == models.Course.id)
            .join(models.Lesson, models.Lesson.section_id == models.Section.id)
            .join(models.Step, models.Step.lesson_id == models.Lesson.id)
            .where(
                models.Step.id == step_id,
                models.Course.slug == course_slug.lower(),
                models.Course.is_published.is_(True)
            )
    )
    course_id = result.scalar_one_or_none()
    if course_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Step not found"
        )
    await require_course_enrollment(course_id, current_user, db)
    return current_user


StepEnrolledUser = Annotated[models.User, Depends(require_step_enrollment)]
StepViewerEnrolledUser = Annotated[models.User, Depends(require_step_viewer_enrollment)]
