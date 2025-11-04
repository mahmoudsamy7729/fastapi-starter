from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import schema
from app.auth.utils.exceptions import UserExceptions, TokenExceptions
from app.core.security import hash_password
from app.core.security import verify_password
from app.core.jwt_handler import (verify_verification_token, verify_reset_token)
from app.users import models



class UserService:
    
    
    @staticmethod
    async def reset_password(token: str, request: schema.ResetPasswordRequest, db: AsyncSession):
        """
        Verify password reset token
        """
        if not token:
            raise TokenExceptions.token_is_missing()
        
        email = verify_reset_token(token)

        user = await db.scalar(
            select(models.User).where(models.User.email == email)
        )

        if not user:
            raise UserExceptions.invalid_credentials()

        hashed_pw = hash_password(request.new_password)
        user.hashed_password = hashed_pw
        await db.commit()
        return {"message": "Password reset successful. You can now log in."}
    

    @staticmethod
    async def change_password(request: schema.ChangePasswordRequest, current_user: models.User ,db: AsyncSession):
        user = await db.scalar(
            select(models.User).where(models.User.email == current_user.email)
        )
        if not user :
            raise UserExceptions.invalid_credentials()
        if not verify_password(request.password, user.hashed_password):
            raise UserExceptions.old_password_incorrect()
        if request.password == request.new_password:
            raise UserExceptions.new_password_same_as_old()
        hashed_pw = hash_password(request.new_password)
        user.hashed_password = hashed_pw
        await db.commit()
        return {"message": "Password changed successfully. You can now log in."}
    

    