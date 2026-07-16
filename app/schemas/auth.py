from pydantic import BaseModel, EmailStr, Field
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


class PasswordResetRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)