from fastapi import APIRouter, status
from app.api.dependencies import CurrentUser, DBSession, OnlyAdmin, TaskEnrolledUser
from app.schemas.submission import SubmissionCreate, SubmissionDetail
from app.services import submission as submission_service

router = APIRouter()


@router.post('', response_model=SubmissionDetail, status_code=status.HTTP_201_CREATED)
async def create_submission(user: TaskEnrolledUser, submissionInfo: SubmissionCreate, db: DBSession):
    return await submission_service.create_submission(
        user_id=user.id,
        submissionInfo=submissionInfo,
        db=db
    )

@router.get('/{submission_id}', response_model=SubmissionDetail)
async def get_my_submission(submission_id: int, user: CurrentUser, db: DBSession):
    return await submission_service.get_submission(submission_id=submission_id, user_id=user.id, db=db, check_for_user=True)


@router.get('/{submission_id}/admin', response_model=SubmissionDetail)
async def get_submission_admin(submission_id: int, admin: OnlyAdmin, db: DBSession):
    return await submission_service.get_submission(submission_id=submission_id, user_id=admin.id, db=db, check_for_user=False)
