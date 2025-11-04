from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from app.auth import schema
from app.users.services.email import email_dependency
from app.core.database import db_dependency
from app.core.security import user_dependency
from app.core.mail import EmailSchema
from app.users.services.user_service import UserService


router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/password/forgot", status_code=status.HTTP_200_OK)
async def forget_password(request: schema.ForgetPasswordRequest, 
                          background_taks: BackgroundTasks, email_service: email_dependency):
    """
    Send link with the token to reset password when user forgets their password
    """
    email_data = EmailSchema(email=[request.email])
    background_taks.add_task(email_service.send_password_reset_email, email_data, {"sub": str(request.email)})
    return {
        "message": "If this email exists, you’ll receive a reset link shortly."
    }


@router.post("/password/reset", status_code=status.HTTP_200_OK)
async def password_reset(token: str, request: schema.ResetPasswordRequest, db: db_dependency):
    """
    Reset Password when User forget their passowrd 
    """
    try:
        reset_password = await UserService.reset_password(token, request, db)
        return reset_password
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/password/change", status_code=status.HTTP_200_OK)
async def password_change( request: schema.ChangePasswordRequest, 
                          current_user: user_dependency ,db: db_dependency):
    """
    Change Password comapre old password and change it 
    """
    try:
        changed = await UserService.change_password(request, current_user, db)
        return changed
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
