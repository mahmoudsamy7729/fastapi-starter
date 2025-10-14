from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from fastapi import HTTPException, status, Request

from app.auth import models, schema
from app.core.security import hash_password
from app.core.security import verify_password
from app.core.jwt_handler import create_access_token, create_refresh_token, verify_refresh_access_token, verify_verification_token


class UserService:
    @staticmethod
    async def create_user(db: AsyncSession, user_in: schema.UserCreate):
        result = await db.execute(select(models.User).where(
            or_(models.User.email == user_in.email), (models.User.username == user_in.username))
            )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ValueError("Email or username already registered")
        
        hashed_pw = hash_password(user_in.password)

        new_user = models.User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=hashed_pw
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    
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
        refresh_token = request.cookies.get("refresh_token")
        tokens = verify_refresh_access_token(refresh_token)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["new_refresh_token"]
        }
    

    @staticmethod
    async def verification_token_verify(token: str, db: AsyncSession):
        user_id = verify_verification_token(token)

        result = await db.execute(select(models.User).where(models.User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_verified:
            return {"message": "Email already verified"}

        user.is_verified = True
        await db.commit()
        return {"message": "Email verified successfully"}
    
