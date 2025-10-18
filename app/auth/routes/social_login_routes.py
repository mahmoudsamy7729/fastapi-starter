from fastapi import APIRouter, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
from app.auth.services.google_oauth_service import GoogleOAuthService



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

    # 👇 Here you can:
    # 1. Check if user exists in DB by email
    # 2. Create user if not exists
    # 3. Generate your own JWT tokens

    return {"user": user_info, "tokens": tokens}
    