# app/schemas/user.py
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


# Request: User Registration
class UserCreate(BaseModel):
    email: EmailStr
    password: str


# Request: User Login
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# Response: User Data
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Response: JWT Token Payload
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    is_admin: bool
