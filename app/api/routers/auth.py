from typing import Annotated
from fastapi import APIRouter, HTTPException, status, Depends, Response, Query
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.user import UserCreate
from app.schemas.auth import AuthResponse, Token, MessageResponse, ForgotPasswordRequest, PasswordResetRequest
from app.api.dependencies import DBSession
from app.services.auth import (
    register_user,
    get_user_id,
    create_password_reset_token,
    request_password_reset,
    verify_password_reset_token as verify_prt,
    reset_password as rpassword
)
from app.core.security import create_access_token


router = APIRouter()

@router.post('/register', response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user: UserCreate,
    db: DBSession   
):
    new_user = await register_user(user, db)
    return {
        "token": {
            "access_token": create_access_token(new_user.id),
            "token_type": "bearer"
        },
        "user": new_user
    }


@router.post('/token', response_model=Token)
async def get_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSession
):
    user_id = await get_user_id(
        email=form_data.username, 
        password=form_data.password, 
        db=db,
        refresh_last_login_at=True
    )
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return {
        "access_token": create_access_token(user_id),
        "token_type": "bearer"
    }

@router.post('/forgot-password', response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: DBSession
):
    await request_password_reset(
        email=data.email,
        db=db
    )

    return MessageResponse(
        message=(
            "The letter has been sent"
        )
    )


@router.get('/reset-password/verify')
async def verify_password_reset_token(token: Annotated[str, Query()], db: DBSession):
    await verify_prt(token=token, db=db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post('/reset-password', status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(passwordResetInfo: PasswordResetRequest, db: DBSession):
    await rpassword(token=passwordResetInfo.token, new_password=passwordResetInfo.new_password, db=db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
