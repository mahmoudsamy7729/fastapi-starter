import httpx
from fastapi import HTTPException, status
from app.core.config import settings

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

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
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get tokens")
            return response.json()

    @staticmethod
    async def get_user_info(access_token: str):
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            

            # 👇 Here you can:
            # 1. Check if user exists in DB by email
            # 2. Create user if not exists
            # 3. Generate your own JWT tokens
            return response.json()
