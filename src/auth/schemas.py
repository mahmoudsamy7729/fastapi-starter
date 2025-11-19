from uuid import UUID
from pydantic import BaseModel, EmailStr
from src.auth.models import Provider


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserRead(UserBase):
    id : UUID
    provider: Provider


class UserCreateRequest(UserBase):
    password: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserLoginResponse(BaseModel):
    token: str
    type: str = "Bearer"
    user: UserRead


class RefreshTokenResponse(BaseModel):
    token: str
    type: str = "Bearer"


class MessageResponse(BaseModel):
    message: str


class ForgetPasswordRequest(BaseModel):
    email: EmailStr


class NewPasswordRequest(BaseModel):
    token: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class LoginCodeRequest(BaseModel):
    email: EmailStr


class LoginWithCodeRequest(BaseModel):
    email: EmailStr
    code: str



