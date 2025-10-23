import httpx
import random
from uuid import UUID
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Depends, status

from app.core.database import get_db
from app.core.config import settings
from app.auth.services.auth_services import UserService

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

db_dependency = Annotated[AsyncSession, Depends(get_db)]

class GoogleOAuthService:
    @staticmethod
    def get_login_url():
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }

        query = "&".join([f"{key}={value}" for key, value in params.items()])
        return f"{GOOGLE_AUTH_URL}?{query}"

    @staticmethod
    async def get_tokens(code: str):
        async with httpx.AsyncClient() as client:
            data = {
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            }
            response = await client.post(GOOGLE_TOKEN_URL, data=data)
            if response.status_code != status.HTTP_200_OK:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get tokens")
            return response.json()

    @staticmethod
    async def get_user_info(access_token: str, db: AsyncSession):
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
            if response.status_code != status.HTTP_200_OK:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get user info")
            
            email = response.json().get("email")
            username = response.json().get("name").replace(" ", "_")+str(random.randint(1000, 9999))
            

            # 👇 Here you can:
            user = await UserService.check_user_exist(db, email)
            if not user:
                user = await UserService.create_new_user_social_register(db, email, username)
            
            tokens = await UserService.generate_tokens_social_login(UUID(str(user)))

            return tokens
