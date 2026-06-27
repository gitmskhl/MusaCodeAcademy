from pydantic import BaseModel
from .user import UserPublicDetailed

class Token(BaseModel):
    access_token: str
    token_type: str


class AuthResponse(BaseModel):
    token: Token
    user: UserPublicDetailed    
