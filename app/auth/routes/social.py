from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, status, Request, Depends, Response
from fastapi.responses import RedirectResponse, JSONResponse


from app.core.database import get_db
from app.auth.utils.responses import auth_response
from app.auth.services.google_oauth_service import GoogleOAuthService
from app.auth.services.github_oauth_service import GithubOAuthService



router = APIRouter(prefix="/auth/social", tags=["Social Auth"])

db_dependency = Annotated[AsyncSession, Depends(get_db)]


@router.get("/login/google/start", status_code=status.HTTP_200_OK)
async def google_login():
    """Redirect user to Google OAuth login."""
    url = GoogleOAuthService.get_login_url()
    return RedirectResponse(url)


@router.get("/callback/google", status_code=status.HTTP_200_OK)
async def google_callback(request: Request, response: Response, db: db_dependency):
    """Handle Google callback and return user info."""
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Code not found"})

    access_token = await GoogleOAuthService.get_tokens(code)
    tokens = await GoogleOAuthService.get_user_info(access_token["access_token"], db)
    return auth_response(response, tokens['access_token'], tokens['refresh_token'])



@router.get("/login/github/start", status_code=status.HTTP_200_OK)
async def github_login():
    """Redirect user to Google OAuth login."""
    url = GithubOAuthService.get_login_url()
    return RedirectResponse(url)


@router.get("/callback/github", status_code=status.HTTP_200_OK)
async def github_callback(request: Request, response: Response, db: db_dependency):
    """Handle Google callback and return user info."""
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": "Code not found"})

    access_token = await GithubOAuthService.get_tokens(code)
    tokens = await GithubOAuthService.get_user_info(access_token, db)
    return auth_response(response, tokens['access_token'], tokens['refresh_token'])
    
    