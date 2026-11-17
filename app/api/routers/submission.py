from fastapi import APIRouter, status
from app.api.dependencies import CurrentUser, DBSession, OnlyAdmin, TaskEnrolledUser
from app.schemas.submission import SubmissionCreate, SubmissionDetail
from app.services import submission as submission_service
from app.schemas.ai_hint import AIHintRequest, AIHintResponse, AIHintStatus
from app.services import ai_hint

router = APIRouter()


@router.get('/ai-hints/status', response_model=AIHintStatus)
async def ai_hint_status(user: CurrentUser, db: DBSession):
    return await ai_hint.get_status(db, user)


@router.post('/{submission_id}/hint', response_model=AIHintResponse)
async def create_ai_hint(submission_id: int, user: CurrentUser, db: DBSession, request: AIHintRequest | None = None):
    return await ai_hint.create_hint(db, user, submission_id, model=request.model if request else None)


@router.post('', response_model=SubmissionDetail, status_code=status.HTTP_201_CREATED)
async def create_submission(user: TaskEnrolledUser, submissionInfo: SubmissionCreate, db: DBSession):
    submission = await submission_service.create_submission(
        user_id=user.id,
        submissionInfo=submissionInfo,
        db=db
    )
    return await submission_service.submission_detail(submission, db)

@router.get('/{submission_id}', response_model=SubmissionDetail)
async def get_my_submission(submission_id: int, user: CurrentUser, db: DBSession):
    submission = await submission_service.get_submission(submission_id=submission_id, user_id=user.id, db=db, check_for_user=True)
    return await submission_service.submission_detail(submission, db)


@router.get('/{submission_id}/admin', response_model=SubmissionDetail)
async def get_submission_admin(submission_id: int, admin: OnlyAdmin, db: DBSession):
    submission = await submission_service.get_submission(submission_id=submission_id, user_id=admin.id, db=db, check_for_user=False)
    return await submission_service.submission_detail(submission, db)
