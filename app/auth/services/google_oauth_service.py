import httpx
import random
from uuid import UUID
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, Depends, status

from app.core.database import get_db
from app.core.config import settings
from app.auth.services.auth_services import AuthService


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
        return f"{settings.google_auth_url}?{query}"

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
            response = await client.post(settings.google_token_url, data=data)
            if response.status_code != status.HTTP_200_OK:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get tokens")
            return response.json()

    @staticmethod
    async def get_user_info(access_token: str, db: AsyncSession):
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(settings.google_userinfo_url, headers=headers)
            if response.status_code != status.HTTP_200_OK:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get user info")
            
            email = response.json().get("email")
            username = response.json().get("name").replace(" ", "_")+str(random.randint(1000, 9999))
            

            # 👇 Here you can:
            user = await AuthService.check_user_exist(db, email)
            if not user:
                user = await AuthService.create_new_user_social_register(db, email, username)
            
            tokens = await AuthService.generate_tokens_social_login(UUID(str(user)))

            return tokens
