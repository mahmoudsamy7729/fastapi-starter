from fastapi import APIRouter, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from app.auth.services.google_oauth_service import GoogleOAuthService
from app.auth.services.github_oauth_service import GithubOAuthService



router = APIRouter(prefix="/auth/social", tags=["Social Auth"])



@router.get("/login/google", status_code=status.HTTP_200_OK)
async def google_login():
    """Redirect user to Google OAuth login."""
    url = GoogleOAuthService.get_login_url()
    return RedirectResponse(url)


@router.get("/callback/google", status_code=status.HTTP_200_OK)
async def google_callback(request: Request):
    """Handle Google callback and return user info."""
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(status_code=400, content={"detail": "Code not found"})

    tokens = await GoogleOAuthService.get_tokens(code)
    user_info = await GoogleOAuthService.get_user_info(tokens["access_token"])


    return {"user": user_info, "tokens": tokens}



@router.get("/login/github", status_code=status.HTTP_200_OK)
async def github_login():
    """Redirect user to Google OAuth login."""
    url = GithubOAuthService.get_login_url()
    return RedirectResponse(url)


@router.get("/callback/github", status_code=status.HTTP_200_OK)
async def github_callback(request: Request):
    """Handle Google callback and return user info."""
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(status_code=400, content={"detail": "Code not found"})

    access_token = await GithubOAuthService.get_tokens(code)
    user_info = await GithubOAuthService.get_user_info(access_token)
    

    return {"user": user_info, "tokens": access_token}
    
    