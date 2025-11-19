from datetime import datetime, UTC, timezone
from uuid import UUID
from fastapi import HTTPException, status, Request
from src.config import settings
from src.jwt import generate_token, verify_token
from src.hashing import hash_password, verify_password
from src.models import RefreshToken
from src.utils import store_refresh_token_in_db, validate_refresh_token, revoke_refresh_token
from src.repository import RefreshTokenRepository
from src.auth import utils, schemas
from src.auth.repository import UserRepository, LoginCodeRepository
from src.auth.models import User, Provider




class UserService:
    @staticmethod
    async def register_user(user_data: schemas.UserCreateRequest, repo: UserRepository) -> User:
        existing_email = await repo.get_by_email(user_data.email)
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
        
        existing_username = await repo.get_by_username(user_data.username)
        if existing_username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
        
        new_user = User(
            email = user_data.email,
            username = user_data.username,
            password = await hash_password(user_data.password),
            provider = Provider.LOCAL
        )
        return await repo.create(new_user)
    

    @staticmethod
    async def login_user(user_data: schemas.UserLoginRequest, repo: UserRepository, token_repo: RefreshTokenRepository) -> tuple[str, User, str]:
        user = await repo.get_by_email(user_data.email)
        if user and await verify_password(user_data.password, user.password):
            if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")
            data = {"sub": str(user.id), "email": user.email, "username": user.username}
            access_token, _, _ = generate_token(data, settings.access_token_expire, settings.access_secret_key)
            refresh_token, jti, exp = generate_token(data, settings.refresh_token_expire, settings.refresh_secret_key)
            await store_refresh_token_in_db(user.id, jti, refresh_token, exp, token_repo)
            return access_token, user, refresh_token
    
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
    
    @staticmethod
    async def refresh_token(request: Request, token_repo: RefreshTokenRepository):
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing.")
        payload = verify_token(refresh_token, settings.refresh_secret_key)

        jti = payload.get("jti")
        old_token = await token_repo.get_by_jti(jti) #type: ignore
        validate_refresh_token(jti, old_token)

        for key in ("iat", "exp", "jti"):
            payload.pop(key, None)
        access_token, _, _ = generate_token(payload, settings.access_token_expire, settings.access_secret_key)
        refresh_token, jti, exp = generate_token(payload, settings.refresh_token_expire, settings.refresh_secret_key)
        new_token = RefreshToken(
            user_id = UUID(payload["sub"]),
            jti = jti,
            token_hash = await hash_password(refresh_token),
            expires_at = exp
        )
        await revoke_refresh_token(new_token, old_token, token_repo)        
        return access_token, refresh_token

        
    @staticmethod
    async def validate_user(token: str, repo: UserRepository) -> bool:
        payload = verify_token(token, settings.validation_secret_key)
        
        user_id = UUID(payload.get('sub'))        
        user = await repo.get_by_id(user_id)

        if user is None: 
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        if user.is_verified :
            return False
        user.is_verified = True 
        await repo.update(user)
        return True


    @staticmethod
    async def forget_password(data: schemas.ForgetPasswordRequest, repo: UserRepository) -> User | None:
        user = await repo.get_by_email(data.email)
        return user


    @staticmethod
    async def new_password(data: schemas.NewPasswordRequest, repo: UserRepository) -> bool:
        payload = verify_token(data.token, settings.validation_secret_key)
        user_id = UUID(payload.get('sub'))        
        user = await repo.get_by_id(user_id)

        if user is None: 
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        user.password = await hash_password(data.password)
        await repo.update(user)
        return True


    @staticmethod 
    async def change_password(data: schemas.ChangePasswordRequest, repo: UserRepository, current_user: User) -> bool:
        if not await verify_password(data.old_password, current_user.password):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Old password isn't correct."
            )

        current_user.password = await hash_password(data.new_password)
        await repo.update(current_user)
        return True


    @staticmethod 
    async def login_code(data: schemas.LoginCodeRequest, user_repo: UserRepository, code_repo: LoginCodeRepository) -> tuple[User, str] :
        user = await user_repo.get_by_email(data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid  email."
            )
        login_code, code = await utils.generate_otp_code(user.id) #type: ignore
        await code_repo.delete(user.id) #type: ignore
        await code_repo.create(login_code)
        return user, code


    @staticmethod
    async def login_with_code(data: schemas.LoginWithCodeRequest, user_repo: UserRepository, code_repo: LoginCodeRepository, token_repo: RefreshTokenRepository):
        user = await user_repo.get_by_email(data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid code or email."
            )
        
        login_code = await code_repo.get_latest_for_user(user.id) #type: ignore
        if not login_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid code or email."
            )
        
        if login_code.expires_at < datetime.now(UTC):
            await code_repo.delete(user.id) #type: ignore
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Code has expired."
            )
        
        if not await verify_password(data.code, login_code.code_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid code or email."
            )
        
        await code_repo.delete(user.id) #type: ignore

        if not user.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")

        user_data = {"sub": str(user.id), "email": user.email, "username": user.username}
        access_token, _, _ = generate_token(user_data, settings.access_token_expire, settings.access_secret_key)
        refresh_token, jti, exp = generate_token(user_data, settings.refresh_token_expire, settings.refresh_secret_key)
        await store_refresh_token_in_db(user.id, jti, refresh_token, exp, token_repo)          
        return access_token, user, refresh_token

        
    @staticmethod 
    async def login_with_google(request: Request, repo: UserRepository, token_repo: RefreshTokenRepository):
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        cookie_state = request.cookies.get("oauth_state_google")
        if not code or not state or not cookie_state:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth callback")
        if state != cookie_state:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
        token = await utils.google_tokens(code) 
        email, username = await utils.get_user_info(token)
        user = await repo.get_by_email(email)
        if not user:
            user = User(
                email = email,
                username = username,
                provider = Provider.GOOGLE,
                is_verified = True
            ) 
            user = await repo.create(user)

        user_data = {"sub": str(user.id), "email": user.email, "username": user.username}
        access_token, _, _ = generate_token(user_data, settings.access_token_expire, settings.access_secret_key)
        refresh_token, jti, exp = generate_token(user_data, settings.refresh_token_expire, settings.refresh_secret_key)
        await store_refresh_token_in_db(user.id, jti, refresh_token, exp, token_repo)        
        return access_token, user, refresh_token
        

    @staticmethod
    async def login_with_github(request: Request, repo: UserRepository, token_repo: RefreshTokenRepository):
        error = request.query_params.get("error")
        if error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub authentication failed")
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        cookie_state = request.cookies.get("oauth_state_github")
        if not code or not state or not cookie_state:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth callback")
        if state != cookie_state:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
        token = await utils.github_tokens(code) 
        email, username = await utils.get_github_user_info(token)
        if email is None:
            email = f"{username}@github.local"
        user = await repo.get_by_email(email)
        if not user:
            user = User(
                email = email,
                username = username,
                provider = Provider.GITHUB,
                is_verified = True
            ) 
            user = await repo.create(user)

        user_data = {"sub": str(user.id), "email": user.email, "username": user.username}
        access_token, _, _ = generate_token(user_data, settings.access_token_expire, settings.access_secret_key)
        refresh_token, jti, exp = generate_token(user_data, settings.refresh_token_expire, settings.refresh_secret_key)
        await store_refresh_token_in_db(user.id, jti, refresh_token, exp, token_repo)         
        return access_token, user, refresh_token


    @staticmethod
    async def deactivate_user(current_user: User, repo: UserRepository):
        current_user.is_active = False #type: ignore
        await repo.update(current_user)
        return True


    
    


    

class ProfileService:
    pass