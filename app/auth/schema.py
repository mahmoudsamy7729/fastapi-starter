from datetime import datetime
from uuid import UUID
from pydantic import EmailStr, Field, BaseModel
from fastapi import  Form
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr = Field (...,  examples=["example@email.com"])
    username: str = Field(..., examples=["example_username"])
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(...,min_length=8, max_length=72, examples=["strongpassword123"])
    
def as_form(
    email: EmailStr = Form(...),
    username: str = Form(...),
    password: str = Form(...)
) -> UserCreate:
    return UserCreate(email=email, username=username, password=password)



class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(UserBase):
    id: UUID
    profile_image: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserCreateResponse(BaseModel):
    message: str
    user: UserRead


class ForgetPasswordRequest(BaseModel):
    email: EmailStr = Field (...,  examples=["example@email.com"])


class ResetPasswordRequest(BaseModel):
    new_password: str


class ChangePasswordRequest(BaseModel):
    password: str
    new_password: str