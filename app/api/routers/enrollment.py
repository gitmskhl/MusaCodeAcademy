from fastapi import APIRouter
from app.schemas.enrollment import EnrollmentWithCourse
from app.api.dependencies import CurrentUser, DBSession
from app.services import enrollment as service_enrollment

router = APIRouter()

@router.get('/me', response_model=list[EnrollmentWithCourse])
async def get_my_enrollments(currentUser: CurrentUser, db: DBSession):
    return await service_enrollment.get_user_enrollments(currentUser.id, db)