from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.auth import schema
from app.auth.sending_emails import get_email_service, EmailService
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.mail import EmailSchema
from app.auth.services import UserService
from app.auth.models import User
from app.core.middlewares.rate_limit import limiter


router = APIRouter(prefix="/auth", tags=["Auth"])


db_dependency = Annotated[AsyncSession, Depends(get_db)]
email_service_dependency = Annotated[EmailService, Depends(get_email_service)]
user_dependency = Annotated[User, Depends(get_current_user)]


@router.post("/register", response_model=schema.UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: schema.UserCreate, background_tasks: BackgroundTasks, 
                        email_service: email_service_dependency, db: db_dependency):
    try:
        new_user = await UserService.create_user(db, user_in)
        email_data = EmailSchema(email=[user_in.email])
        background_tasks.add_task(email_service.send_verification_email, email_data, {"sub": str(new_user.id)})
        return {
            "message": "Account created successfully, Check email to verify your account",
            "user": new_user 
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    

@router.post("/login", status_code=status.HTTP_200_OK)
async def login(user_in: schema.UserLogin, response: Response, db: db_dependency):
    tokens =  await UserService.login_user(user_in, db)
    response.set_cookie(
            key="refresh_token",
            value=tokens['refresh_token'],
            httponly=True,     # prevents JS access
            secure=False,       # use HTTPS in production
            samesite="lax",    # 'none' if frontend is on a different domain
            max_age=7*24*60*60 # cookie lifetime in seconds
        )
    return {
        "access_token": tokens['access_token'],
        "token_type": "bearer"
    }


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(request: Request, response: Response):
    tokens =  await UserService.refresh_token(request)
    response.set_cookie(
            key="refresh_token",
            value=tokens['refresh_token'],
            httponly=True,     # prevents JS access
            secure=False,       # use HTTPS in production
            samesite="lax",    # 'none' if frontend is on a different domain
            max_age=7*24*60*60 # cookie lifetime in seconds
        )
    return {
        "access_token": tokens['access_token'],
        "token_type": "bearer"
    }


@router.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(token: str, db: db_dependency):
    try:
        verified = await UserService.verification_token_verify(token, db)
        return verified
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    

@router.get("/protected")
async def protected_route(current_user: user_dependency):
    return {"message": f"Hello {current_user.username}!"}

