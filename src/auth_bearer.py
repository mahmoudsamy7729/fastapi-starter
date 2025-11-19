from uuid import UUID
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy import select

from src.config import settings
from src.database import db_dependency
from src.jwt import verify_token
from src.auth.models import User


oauth2_schema = HTTPBearer()


async def get_user(db : db_dependency, token: str = Depends(oauth2_schema)) -> User :
    payload = verify_token(token.credentials, settings.access_secret_key)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user_id = UUID(sub)     
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    return user


async def get_active_user(current_user: User = Depends(get_user)) -> User:
    if current_user is None :
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    if current_user.is_verified is False or current_user.is_active is False :
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active or verified"
        )
    return current_user


async def get_not_active_user(current_user: User = Depends(get_user)) -> User:
    if current_user is None :
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    return current_user
    
non_active_user_dependency = Annotated[User, Depends(get_not_active_user)]
user_dependency = Annotated[User, Depends(get_active_user)]




