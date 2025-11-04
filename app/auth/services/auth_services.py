import secrets
from pathlib import Path
import uuid
from uuid import UUID
from datetime import datetime, timedelta, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, insert, desc
from fastapi import HTTPException, status, Request, UploadFile, File

from app.auth import schema
from app.auth.utils.exceptions import UserExceptions, TokenExceptions
from app.core.security import hash_password
from app.core.security import verify_password
from app.core.jwt_handler import (create_access_token, create_refresh_token,
                                verify_refresh_token, verify_verification_token,
                                verify_reset_token)
from app.users.models import User
from app.auth.models import LoginCode


# Folder to save uploaded images
UPLOAD_DIR = Path("uploads/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class AuthService:
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
        email = user_in.email.strip().casefold()
        username = user_in.username.strip()
        existing_user = await db.scalar(
            select(User).where(
                or_(
                    User.email == email,
                    User.username == username
                )
            )
        )
        if existing_user:
            raise UserExceptions.already_exists()
        
        
        hashed_pw = hash_password(user_in.password)

        new_user = User(
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
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        user.profile_image = image_path
        await db.commit()
        await db.refresh(user)


    @staticmethod
    async def check_user_exist(db: AsyncSession, email: str):
        result = await db.execute(select(User.id).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            return user
        return False
    

    @staticmethod
    async def create_new_user_social_register(db: AsyncSession, email: str, username: str):
        new_user = User(
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
    async def authenticate_user(user_in: schema.UserLogin, db: AsyncSession) -> User | bool:
        """Verify user credentials."""
        user = await db.scalar(
                select(User).where(User.email == user_in.email)
            )
        if not user or not verify_password(user_in.password, user.hashed_password):
            # logging
            return False
        return user
    
    
    @staticmethod
    async def login_user(user_in: schema.UserLogin, db: AsyncSession):
        """Login user and return JWT token."""
        user = await AuthService.authenticate_user(user_in, db)
        if not user:
           raise UserExceptions.invalid_credentials()
        
        if not user.is_verified:
            raise UserExceptions.email_not_verified()
        
        data = {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username
        }
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }


    @staticmethod
    async def refresh_token(request: Request):
        """
        Verify refresh token and return access and refresh tokens
        """
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise TokenExceptions.token_is_missing()
        
        tokens = verify_refresh_token(refresh_token)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"]
        }
    

    @staticmethod
    async def verification_token_verify(token: str, db: AsyncSession):
        """
        Verify Token for email verification
        """
        if not token:
            raise TokenExceptions.token_is_missing()
        
        user_id = verify_verification_token(token)

        user = await db.scalar(
                select(User).where(User.id == user_id)
            )

        if not user:
            raise UserExceptions.invalid_credentials()

        if user.is_verified:
            return {"message": "Email already verified"}

        user.is_verified = True
        await db.commit()
        return {"message": "Email verified successfully"}
    

    @staticmethod
    async def generate_login_code(request: schema.ForgetPasswordRequest, db:AsyncSession):
        user = await db.scalar(
            select(User).where(User.email == request.email)
        )
        if not user :
            raise UserExceptions.invalid_credentials()
        
        code = f"{secrets.randbelow(1000000):06}"
        hashed_code = hash_password(code)
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        await db.execute(insert(LoginCode).values(
            user_id=user.id,
            code_hash=hashed_code,
            expires_at=expires_at
        ))
        await db.commit()
        return code
    

    @staticmethod
    async def verify_login_code(user: schema.UserLoginWithCode, db: AsyncSession):
        user_id = await db.scalar(
            select(User.id).where(User.email == user.email)
        )
        if not user_id :
            raise UserExceptions.invalid_credentials()
        
        login_code = await db.scalar(
            select(LoginCode).where(LoginCode.user_id == user_id).order_by(desc(LoginCode.created_at))
        )

        if not login_code:
            raise UserExceptions.login_code_expired()
        
        if login_code.expires_at < datetime.now(UTC):
            await db.delete(login_code)
            await db.commit()
            raise UserExceptions.login_code_expired()
        
        if not verify_password(user.code, login_code.code_hash):
            raise UserExceptions.invalid_login_code()
        
        await db.delete(login_code)
        await db.commit()

        access_token = create_access_token({"sub": str(user_id)})
        refresh_token = create_refresh_token({"sub": str(user_id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        

        


    


