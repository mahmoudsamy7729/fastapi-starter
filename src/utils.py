from datetime import datetime, timezone, UTC
from uuid import UUID
from fastapi_mail import ConnectionConfig
from fastapi import status, HTTPException
from pydantic import BaseModel, EmailStr
from src.config import settings
from src.models import RefreshToken
from src.hashing import hash_password
from src.repository import RefreshTokenRepository


conf = ConnectionConfig(
    MAIL_USERNAME=settings.smtp_user,
    MAIL_PASSWORD=settings.smtp_password,   # type: ignore
    MAIL_FROM=settings.smtp_user,
    MAIL_PORT=settings.smtp_port,
    MAIL_SERVER=settings.smtp_host,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER='templates/email' # type: ignore
)


class EmailSchema(BaseModel):
    email: list[EmailStr]



async def store_refresh_token_in_db(user_id: UUID, jti: str, refresh_token: str, exp: datetime, token_repo: RefreshTokenRepository):
    token = RefreshToken(
        user_id = user_id,
        jti = jti,
        token_hash = await hash_password(refresh_token),
        expires_at = exp
    )
    await token_repo.revoke_all_for_user(user_id)
    await token_repo.create(token)



def validate_refresh_token(jti: str | None, old_token: RefreshToken | None):
    if jti is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token payload",
        )

    if old_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not recognized",
        )

    if old_token.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )


async def revoke_refresh_token(new_token: RefreshToken, old_token: RefreshToken, token_repo: RefreshTokenRepository):
    await token_repo.create(new_token) 
    old_token.replaced_by_jti = new_token.jti
    old_token.revoked = True
    old_token.revoked_at = datetime.now(timezone.utc)  
    await token_repo.update(old_token)   