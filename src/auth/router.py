from fastapi import APIRouter, Response, BackgroundTasks, status, Request
from fastapi.responses import RedirectResponse
from src.auth import schemas, utils
from src.auth.service import UserService
from src.auth.dependencies import repo_dependency, email_dependency, code_dependency
from src.auth_bearer import  user_dependency, non_active_user_dependency
from src.dependencies import token_depedency
from src.rate_limiter import limiter


router = APIRouter()

@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: schemas.UserCreateRequest, repo: repo_dependency,
                        background: BackgroundTasks, email: email_dependency):
    user = await UserService.register_user(user_data, repo)
    background.add_task(email.send_verification_email, user.email, user.id) 
    return user


@router.post("/login", response_model=schemas.UserLoginResponse, status_code=status.HTTP_200_OK)
async def login_user(user_data: schemas.UserLoginRequest, repo: repo_dependency, token_repo: token_depedency,
                    response: Response):
    access_token, user, refresh_token = await UserService.login_user(user_data, repo, token_repo)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,       # True in production (HTTPS)
        samesite="lax",     # likely "none" in prod if cross-site
        max_age=7*24*60*60
    )

    return {"token": access_token, "user": user}


@router.post("/refresh-token", response_model=schemas.RefreshTokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(request: Request, response: Response, token_repo: token_depedency):
    access_token, refresh_token = await UserService.refresh_token(request, token_repo)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,       # True in production (HTTPS)
        samesite="lax",     # likely "none" in prod if cross-site
        max_age=7*24*60*60
    )
    return {"token": access_token}


@router.get("/verify", response_model=schemas.MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def verify_email(token: str, repo: repo_dependency):
    verify = await UserService.validate_user(token, repo)
    if verify:
        return{"message": "Email is Verified"}
    return{"message": "Email is already Verified"}


@router.post("/request/verify", response_model=schemas.MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_verify_email(current_user: non_active_user_dependency, 
                               background: BackgroundTasks, email: email_dependency):
    if current_user.is_verified: 
        return {"message": "Email is already verified"}
    background.add_task(email.send_verification_email, current_user.email, current_user.id) 
    return {"message": "New Verification Email has been sent"}


@router.post("/forget-password", response_model=schemas.MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def forget_password(data: schemas.ForgetPasswordRequest, repo: repo_dependency,
                          background: BackgroundTasks, email: email_dependency):
    user = await UserService.forget_password(data, repo)
    if user:
        background.add_task(email.send_password_reset_email, user.email, user.id) 
    return {"message": "If an account with this email exists, a password reset link has been sent."}


@router.post("/new-password", response_model=schemas.MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def new_password(data: schemas.NewPasswordRequest, repo: repo_dependency):
    success = await UserService.new_password(data, repo)
    if success:
        return {"message": "Password has been changed successfuly"}


@router.post("/change-password", response_model=schemas.MessageResponse, status_code=status.HTTP_200_OK)
async def change_password(data: schemas.ChangePasswordRequest, repo: repo_dependency, current_user: user_dependency):
    success = await UserService.change_password(data, repo, current_user)
    if success:
        return {"message": "Password has been changed successfuly"}


@router.post("/request/login-code")
async def request_login_code(data: schemas.LoginCodeRequest, user_repo:repo_dependency, code_repo: code_dependency,
                            background: BackgroundTasks, email: email_dependency):
    result = await UserService.login_code(data, user_repo, code_repo)
    if result:
        user, code = result
        background.add_task(email.send_login_code, user.email, code) 
    return {"message": "If an account with this email exists, a login code has been sent."}
    

@router.post("/login/code", response_model=schemas.UserLoginResponse, status_code=status.HTTP_200_OK)
async def login_with_code(data: schemas.LoginWithCodeRequest, response: Response,
                        user_repo:repo_dependency, code_repo: code_dependency, token_repo: token_depedency):
    access_token, user, refresh_token = await UserService.login_with_code(data, user_repo, code_repo, token_repo)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,       # True in production (HTTPS)
        samesite="lax",     # likely "none" in prod if cross-site
        max_age=7*24*60*60
    )
    return {"token": access_token, "user": user}


@router.get("/google/login")
async def login_with_google():
    uri, state = utils.get_google_login_url()
    redirect_response = RedirectResponse(uri)
    redirect_response.set_cookie(
        "oauth_state_google",
        state,
        httponly=True,
        secure=True,   # True in production with HTTPS
        samesite="lax" # or "none" if cross-site redirect needs it
    )
    return redirect_response


@router.get("/auth/social/callback/google", response_model=schemas.UserLoginResponse, status_code=status.HTTP_200_OK)
async def google_callback(response: Response, request: Request, repo:repo_dependency, token_repo: token_depedency):
    access_token, user, refresh_token = await UserService.login_with_google(request, repo, token_repo)
    response.delete_cookie("oauth_state_google")
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,       # True in production (HTTPS)
        samesite="lax",     # likely "none" in prod if cross-site
        max_age=7*24*60*60
    )
    return {"token": access_token, "user": user}


@router.get("/github/login")
async def login_with_github():
    uri, state = utils.get_github_login_url()
    redirect_response = RedirectResponse(uri)
    redirect_response.set_cookie(
        "oauth_state_github",
        state,
        httponly=True,
        secure=True,   # True in production with HTTPS
        samesite="lax" # or "none" if cross-site redirect needs it
    )
    return redirect_response


@router.get("/auth/social/callback/github", response_model=schemas.UserLoginResponse, status_code=status.HTTP_200_OK)
async def github_callback(response: Response, request: Request, repo:repo_dependency, token_repo: token_depedency):
    access_token, user, refresh_token = await UserService.login_with_github(request, repo, token_repo)
    response.delete_cookie("oauth_state_github")
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,       # True in production (HTTPS)
        samesite="lax",     # likely "none" in prod if cross-site
        max_age=7*24*60*60
    )
    return {"token": access_token, "user": user}


@router.post("/deactivate", response_model=schemas.MessageResponse, status_code=status.HTTP_202_ACCEPTED)
async def user_deactivate(current_user: user_dependency, repo: repo_dependency):
    success = await UserService.deactivate_user(current_user, repo)
    if success:
        return {"message": "User deactivated."}
