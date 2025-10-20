import httpx
from fastapi import HTTPException, status
from app.core.config import settings


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_API = "https://api.github.com/user"
GITHUB_EMAILS = "https://api.github.com/user/emails"


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
                raise HTTPException(status_code=400, detail="GitHub token exchange failed")
            return access_token

    @staticmethod
    async def get_user_info(access_token: str):
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(GITHUB_USER_API, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to get user info")
            email_res = await client.get(GITHUB_EMAILS, headers=headers)
            emails = email_res.json()
            primary_email = next((e["email"] for e in emails if e["primary"]), None)
            email = primary_email

            user_info = response.json()
            github_id = user_info.get("id")
            name = user_info.get("login")

            # 👇 Here you can:
            # 1. Check if user exists in DB by email
            # 2. Create user if not exists
            # 3. Generate your own JWT tokens

            return {
                "github_id": github_id,
                "name": name,
                "email": email
            }
