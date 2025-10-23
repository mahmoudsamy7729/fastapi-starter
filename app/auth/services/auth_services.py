import secrets
import os
from pathlib import Path
import uuid
from uuid import UUID
from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, insert, desc
from fastapi import HTTPException, status, Request, UploadFile, File

from app.auth import models, schema
from app.core.security import hash_password
from app.core.security import verify_password
from app.core.jwt_handler import (create_access_token, create_refresh_token,
                                verify_refresh_access_token, verify_verification_token,
                                verify_reset_token)


# Folder to save uploaded images
UPLOAD_DIR = Path("uploads/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class UserService:
    @staticmethod
    async def upload_image(image: UploadFile = File(...)):
         # 1. Validate file type (optional)
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image.")
        
        file_extension = image.filename.split(".")[-1]
        unique_name = f"{uuid.uuid4()}.{file_extension}"
        file_location = UPLOAD_DIR / unique_name

        
        with open(file_location, "wb") as buffer:
            buffer.write(await image.read())

        return unique_name

    
    @staticmethod
    async def create_user(db: AsyncSession, user_in: schema.UserCreate):
        """
        Create user and save to the DB
        """
        result = await db.execute(
            select(models.User).where(
                or_(models.User.email == user_in.email, models.User.username == user_in.username)
            )
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ValueError("Email or username already registered")
        
        
        hashed_pw = hash_password(user_in.password)

        new_user = models.User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=hashed_pw,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    
    
    
    @staticmethod
    async def update_user_profile_image(db, user_id: str, image_path: str):
        user = await db.get(models.User, user_id)
        if not user:
            raise ValueError("User not found")
        user.profile_image = image_path
        await db.commit()
        await db.refresh(user)


    @staticmethod
    async def check_user_exist(db: AsyncSession, email: str):
        result = await db.execute(select(models.User.id).where(models.User.email == email))
        user = result.scalar_one_or_none()
        if user:
            return user
        return False
    

    @staticmethod
    async def create_new_user_social_register(db: AsyncSession, email: str, username: str):
        new_user = models.User(
            email=email,
            username=username,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user.id
    
    @staticmethod
    async def generate_tokens_social_login(user_id: UUID):
        access_token = create_access_token({"sub": str(user_id)})
        refresh_token = create_refresh_token({"sub": str(user_id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }



    @staticmethod
    async def authenticate_user(user_in: schema.UserLogin, db: AsyncSession):
        """Verify user credentials."""
        stmt = select(models.User).where(models.User.email == user_in.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(user_in.password, user.hashed_password):
            return None
        return user
    
    
    @staticmethod
    async def login_user(user_in: schema.UserLogin, db: AsyncSession):
        """Login user and return JWT token."""
        user = await UserService.authenticate_user(user_in, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before accessing this resource"
            )
        

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    
    @staticmethod
    async def refresh_token(request: Request):
        """
        Verify refresh token and return access and refresh tokenss
        """
        refresh_token = request.cookies.get("refresh_token")
        tokens = verify_refresh_access_token(refresh_token)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["new_refresh_token"]
        }
    

    @staticmethod
    async def verification_token_verify(token: str, db: AsyncSession):
        """
        Verify Token for email verification
        """
        user_id = verify_verification_token(token)

        result = await db.execute(select(models.User).where(models.User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if user.is_verified:
            return {"message": "Email already verified"}

        user.is_verified = True
        await db.commit()
        return {"message": "Email verified successfully"}
    

    @staticmethod
    async def reset_password(token: str, request: schema.ResetPasswordRequest, db: AsyncSession):
        """
        Verify password reset token
        """
        email = verify_reset_token(token)

        result = await db.execute(select(models.User).where(models.User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        hashed_pw = hash_password(request.new_password)
        user.hashed_password = hashed_pw
        await db.commit()
        return {"message": "Password reset successful. You can now log in."}
    

    @staticmethod
    async def change_password(request: schema.ChangePasswordRequest, current_user: models.User ,db: AsyncSession):
        result = await db.execute(select(models.User).where(models.User.email == current_user.email))  
        user = result.scalar_one_or_none()
        if not user :
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Old password isn't correct")
        hashed_pw = hash_password(request.new_password)
        user.hashed_password = hashed_pw
        await db.commit()
        return {"message": "Password changed successfully. You can now log in."}
    

    @staticmethod
    async def generate_login_code(request: schema.ForgetPasswordRequest, db:AsyncSession):
        result = await db.execute(select(models.User).where(models.User.email == request.email)) 
        user = result.scalar_one_or_none()
        if not user :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
        
        code = f"{secrets.randbelow(1000000):06}"
        hashed_code = hash_password(code)
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        await db.execute(insert(models.LoginCode).values(
            user_id=user.id,
            code_hash=hashed_code,
            expires_at=expires_at
        ))
        await db.commit()
        return code
    

    @staticmethod
    async def verify_login_code(email: str, code: str, db: AsyncSession):
        result = await db.execute(select(models.User.id).where(models.User.email == email)) 
        user_id = result.scalar_one_or_none()
        if not user_id :
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found")
        
        result = await db.execute(
        select(models.LoginCode).where(models.LoginCode.user_id == user_id).order_by(desc(models.LoginCode.created_at))
        .limit(1)
        )
        login_code = result.scalar_one_or_none()
        if not login_code:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No code found or expired")
        
        if login_code.expires_at < datetime.now(UTC):
            await db.delete(login_code)
            await db.commit()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Code expired")
        
        if not verify_password(code, login_code.code_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
        
        await db.delete(login_code)
        await db.commit()

        access_token = create_access_token({"sub": str(user_id)})
        refresh_token = create_refresh_token({"sub": str(user_id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        

        


    


