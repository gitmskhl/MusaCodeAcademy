from pydantic import BaseModel, EmailStr
from .user import UserPublicDetailed

class Token(BaseModel):
    access_token: str
    token_type: str


class AuthResponse(BaseModel):
    token: Token
    user: UserPublicDetailed    


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str