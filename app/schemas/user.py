from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from app.enums import UserRole

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = Field(min_length=2, max_length=20)
    last_name: str = Field(min_length=2, max_length=20)
    

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    first_name: str
    last_name: str
    role: UserRole


class UserPublicDetailed(UserPublic):
    email: EmailStr


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=2, max_length=20)
    last_name: str | None = Field(default=None, min_length=2, max_length=20)
    

class UserPrivate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime