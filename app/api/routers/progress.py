from fastapi import APIRouter, status

from app.api.dependencies import CurrentUser, DBSession
from app.schemas.progress import (
    CourseProgress,
    CourseSectionsProgress,
    LessonProgress,
    StepProgressPublic,
    StepProgressStatus,
)
from app.services import progress as service_progress

router = APIRouter()


@router.get(
    "/me/courses",
    response_model=list[CourseProgress],
)
async def get_my_courses_progress(
    currentUser: CurrentUser,
    db: DBSession,
):
    return await service_progress.get_my_courses_progress(
        user_id=currentUser.id,
        db=db,
    )


@router.get(
    "/courses/{course_id}/sections",
    response_model=CourseSectionsProgress,
)
async def get_course_sections_progress(
    course_id: int,
    currentUser: CurrentUser,
    db: DBSession,
):
    return await service_progress.get_course_sections_progress(
        course_id=course_id,
        user_id=currentUser.id,
        db=db,
    )


@router.get(
    "/lessons/{lesson_id}",
    response_model=LessonProgress,
)
async def get_lesson_progress(
    lesson_id: int,
    currentUser: CurrentUser,
    db: DBSession,
):
    return await service_progress.get_lesson_progress(
        lesson_id=lesson_id,
        user_id=currentUser.id,
        db=db,
    )


@router.get(
    "/steps/{step_id}",
    response_model=StepProgressStatus,
)
async def get_step_progress(
    step_id: int,
    currentUser: CurrentUser,
    db: DBSession,
):
    completed = await service_progress.is_step_completed(
        step_id=step_id,
        user_id=currentUser.id,
        db=db,
    )
    return StepProgressStatus(completed=completed)


@router.post(
    "/steps/{step_id}",
    response_model=StepProgressPublic,
    status_code=status.HTTP_201_CREATED,
)
async def complete_step(
    step_id: int,
    currentUser: CurrentUser,
    db: DBSession,
):
    return await service_progress.complete_step(
        step_id=step_id,
        user_id=currentUser.id,
        db=db,
    )


@router.delete(
    "/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def uncomplete_step(
    step_id: int,
    currentUser: CurrentUser,
    db: DBSession,
):
    await service_progress.uncomplete_step(
        step_id=step_id,
        user_id=currentUser.id,
        db=db,
    )
