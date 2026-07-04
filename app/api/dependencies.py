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