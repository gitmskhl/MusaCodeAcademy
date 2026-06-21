from datetime import UTC, datetime, timedelta
import jwt
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.exceptions import InvalidTokenError


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

password_hasher = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hasher.verify(password, hashed_password)


def create_access_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    }
    return jwt.encode(
        payload=payload,
        key=settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm
    )


def verify_access_token(token: str) -> int:
    try:
        payload = jwt.decode(
            jwt=token,
            key=settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise InvalidTokenError
        return int(user_id)
    except (jwt.InvalidTokenError, ValueError):
        raise InvalidTokenError