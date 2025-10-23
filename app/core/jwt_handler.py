from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import status, HTTPException
from app.core.config import settings
from app.auth.utils.exceptions import TokenExcpetions


def create_access_token(data: dict) -> str :
    """
    Generate JWT access token
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_access_token(token: str) -> dict:
    """
    Verify JWT access token
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        # Extract subject (user ID)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise TokenExcpetions.token_excep(status.HTTP_401_UNAUTHORIZED, "Could not validate access token")

        return payload

    except JWTError:
        raise TokenExcpetions.token_excep(status.HTTP_401_UNAUTHORIZED, "Could not validate access token")


def create_refresh_token(data: dict) -> str :
    """
    Generate JWT refresh token
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.refresh_token_expire_minutes)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.refresh_secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_refresh_access_token(refresh_token: str) -> dict:
    """
    Verify JWT refresh token
    """
    if not refresh_token:
        raise TokenExcpetions.token_excep(status.HTTP_401_UNAUTHORIZED, "Token is missing")

    try:
        payload = jwt.decode(
            refresh_token,
            settings.refresh_secret_key,
            algorithms=[settings.algorithm]
        )

        # Extract subject (user ID)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise TokenExcpetions.token_excep(status.HTTP_401_UNAUTHORIZED, "Could not validate refresh token")
        
        access_token = create_access_token({"sub": str(user_id)})
        new_refresh_token = create_refresh_token({"sub": str(user_id)})
        
        return {
            "access_token": access_token,
            "new_refresh_token": new_refresh_token
        }

    except JWTError:
        raise TokenExcpetions.token_excep(status.HTTP_401_UNAUTHORIZED, "Could not validate refresh token")


def create_verifcation_token(data: dict) -> str :
    """
    Generate JWT Email Verification - Reset token
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.verification_token_expire_minutes)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.verification_secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_verification_token(verification_token: str) -> str:
    """
    Verify JWT verification token
    """
    if not verification_token:
        raise TokenExcpetions.token_excep(status.HTTP_401_UNAUTHORIZED, "Token is missing")

    try:
        payload = jwt.decode(
            verification_token,
            settings.verification_secret_key,
            algorithms=[settings.algorithm],
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid token")

        return user_id

    except ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Verification link expired")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
    

def verify_reset_token(verification_token: str) -> str:
    """
    Verify JWT reset token
    """
    if not verification_token:
        raise TokenExcpetions.token_excep(status.HTTP_401_UNAUTHORIZED, "Token is missing")
    
    try:
        payload = jwt.decode(
            verification_token,
            settings.verification_secret_key,
            algorithms=[settings.algorithm],
        )
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")

        return email

    except ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Verification link expired")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid token")



