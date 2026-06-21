from fastapi import APIRouter
from app.models import User
from app.api.dependencies import CurrentUser
from app.schemas.user import UserPrivate

router = APIRouter()

@router.get('/me', response_model=UserPrivate)
async def get_me(
    current_user: CurrentUser
):
    return current_user