from pydantic import BaseModel
from .user import UserPublic

class Token(BaseModel):
    access_token: str
    token_type: str


class AuthResponse(BaseModel):
    token: Token
    user: UserPublic    
