import secrets, random, httpx
from urllib.parse import urlencode
from uuid import UUID
from datetime import datetime, timedelta, UTC
from fastapi import HTTPException, status
from src.hashing import hash_password
from src.auth.models import LoginCode
from src.config import settings



async def generate_otp_code(user_id: UUID) -> tuple[LoginCode, str]:
    code = f"{secrets.randbelow(1000000):06}"
    hashed_code = await hash_password(code)
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    return LoginCode(
        user_id = user_id,
        code_hash  = hashed_code,
        expires_at = expires_at
    ), code


def get_google_login_url():
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "state": state,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    query = urlencode(params)
    url = f"{settings.google_auth_url}?{query}"
    return url, state


async def google_tokens(code: str):
    for _ in range(0,3):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                data = {
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                }
                response = await client.post(settings.google_token_url, data=data)
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as e:
            continue
            
        except httpx.HTTPStatusError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google returned invalid response"
            )

        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid JSON from Google"
            )
        
    raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google temporarily unavailable"
        )
        

async def get_user_info(token: dict):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token['access_token']}"} 
        response = await client.get(settings.google_userinfo_url, headers=headers)
        response.raise_for_status()
        email = response.json().get("email")
        username = response.json().get("name").replace(" ", "_")+str(random.randint(1000, 9999))
        return email , username
    

def get_github_login_url():
    state = secrets.token_urlsafe(32)
    params = {
    "client_id": settings.github_client_id,
    "state": state,
    "redirect_uri": settings.github_redirect_uri,
    "scope": "user:email",
    }
    query = urlencode(params)
    url = f"{settings.github_authorize_url}?{query}"
    return url, state


async def github_tokens(code: str):    
            
        for _ in range(0,3):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    token_res = await client.post(
                        settings.github_token_url,
                        data={
                            "client_id": settings.github_client_id,
                            "client_secret": settings.github_client_secret,
                            "code": code,
                            "redirect_uri": settings.github_redirect_uri,
                        },
                        headers={"Accept": "application/json"},
                    )
                    token_res.raise_for_status()

                    token_data = token_res.json()
                    access_token = token_data.get("access_token")
                    if not access_token:
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub token exchange failed")
                    return access_token
            except httpx.RequestError as e:
                continue
            
            except httpx.HTTPStatusError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="GitHub returned invalid response"
                )

            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invalid JSON from GitHub"
                )
            
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub temporarily unavailable"
        )


async def get_github_user_info(token: str):
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(settings.github_user_api, headers=headers)
        response.raise_for_status()
        email_res = await client.get(settings.github_emails, headers=headers)
        email_res.raise_for_status()
        emails = email_res.json()
        primary_email = next((e["email"] for e in emails if e["primary"]), None)
        email = primary_email
        username = response.json().get("login")

        return email, username
