import httpx
from fastapi import HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from uuid import UUID


from app.core.config import settings
from app.core.database import get_db
from app.auth.services.auth_services import UserService


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_API = "https://api.github.com/user"
GITHUB_EMAILS = "https://api.github.com/user/emails"



db_dependency = Annotated[AsyncSession, Depends(get_db)]

class GithubOAuthService:
    @staticmethod
    def get_login_url():
        params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "user:email",
        }
        url = f"{GITHUB_AUTHORIZE_URL}?client_id={params['client_id']}&redirect_uri={params['redirect_uri']}&scope={params['scope']}"
        return url

    @staticmethod
    async def get_tokens(code: str):
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_redirect_uri,
                },
                headers={"Accept": "application/json"},
            )

            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub token exchange failed")
            return access_token

    @staticmethod
    async def get_user_info(access_token: str, db: AsyncSession):
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(GITHUB_USER_API, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to get user info")
            email_res = await client.get(GITHUB_EMAILS, headers=headers)
            emails = email_res.json()
            primary_email = next((e["email"] for e in emails if e["primary"]), None)
            email = primary_email

            username = response.json().get("login")

            if email is not None:
                user = await UserService.check_user_exist(db, email)
                if not user:
                    user = await UserService.create_new_user_social_register(db, email, username)
                
                tokens = await UserService.generate_tokens_social_login(UUID(str(user)))

            return tokens
