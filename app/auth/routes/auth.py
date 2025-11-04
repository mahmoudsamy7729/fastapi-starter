from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, BackgroundTasks, File, UploadFile
from typing import Annotated, Union

from app.auth import schema
from app.auth.utils.responses import auth_response
from app.auth.services.email import email_dependency
from app.core.database import db_dependency
from app.core.mail import EmailSchema
from app.auth.services.auth_services import AuthService
from pydantic import ValidationError as validationError


router = APIRouter(prefix="/auth", tags=["Auth"])




@router.post("/register", response_model=schema.UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def register_user(background_tasks: BackgroundTasks, email_service: email_dependency, 
                db: db_dependency, user_in: schema.UserCreate = Depends(schema.as_form),
                profile_image: Union[UploadFile, None, str] = File(None)):
    """
    Register user to the system 
    """
    try:
        new_user = await AuthService.create_user(db, user_in)
        # 2️⃣ If image was uploaded, store it and update the user record
        if profile_image:
            image_path = await AuthService.upload_image(profile_image)
            await AuthService.update_user_profile_image(db, new_user.id, image_path)
        email_data = EmailSchema(email=[user_in.email])
        background_tasks.add_task(email_service.send_verification_email, email_data, {"sub": str(new_user.id)})
        return {
            "message": "Account created successfully, Check email to verify your account",
            "user": new_user,
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except validationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )
  
    
@router.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(token: str, db: db_dependency):
    """
    Email Verification after user register
    """
    try:
        verified = await AuthService.verification_token_verify(token, db)
        return verified
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", status_code=status.HTTP_200_OK)
async def login(user_in: schema.UserLogin, response: Response, db: db_dependency):
    """
    User Login (Email , Password)
    """
    tokens =  await AuthService.login_user(user_in, db)
    return auth_response(response, tokens['access_token'], tokens['refresh_token'])


@router.post("/login/code/request", status_code=status.HTTP_200_OK)
async def request_login_code(request: schema.ForgetPasswordRequest, background_taks: BackgroundTasks, 
                             email_service: email_dependency, db: db_dependency):
    """
    Request Code to login with (one time use)
    """
    try:
        code = await AuthService.generate_login_code(request, db)
        email_data = EmailSchema(email=[request.email])
        background_taks.add_task(email_service.send_login_code,email_data, code)
        return {
            "message": "The code has been sent to your email"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    

@router.post("/login/code/verify", status_code=status.HTTP_200_OK)
async def login_with_code(user: schema.UserLoginWithCode, response: Response, db: db_dependency):
    """
    User Login with code (Single time use)
    """
    try:
        tokens = await AuthService.verify_login_code(user, db)
        return auth_response(response, tokens['access_token'], tokens['refresh_token'])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    

@router.post("/token/refresh", status_code=status.HTTP_200_OK)
async def refresh_token(request: Request, response: Response):
    """
    Refresh access token frontend should hit this endpoint every x min to keep the user logged in
    """
    tokens =  await AuthService.refresh_token(request)
    return auth_response(response, tokens['access_token'], tokens['refresh_token'])

    




