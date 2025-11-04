from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from app.core.config import settings
from app.auth.utils.exceptions import TokenExceptions


def create_access_token(data: dict) -> str :
    """
    Generate JWT access token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    issued_at = datetime.now(timezone.utc)
    to_encode.update({"exp": expire, "iat": issued_at})

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_access_token(token: str) -> dict:
    """
    Verify JWT access token
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get('sub')
        if user_id is None:
            raise TokenExceptions.invalid_payload()
        
        return payload

    except ExpiredSignatureError:
        raise TokenExceptions.expired_token()
    
    except JWTError:
        raise TokenExceptions.token_exception()


def create_refresh_token(data: dict) -> str :
    """
    Generate JWT refresh token
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.refresh_token_expire_minutes)
    issued_at = datetime.now(timezone.utc)
    to_encode.update({"exp": expire, "iat": issued_at})

    return jwt.encode(to_encode, settings.refresh_secret_key,algorithm=settings.algorithm)


def verify_refresh_token(refresh_token: str) -> dict:
    """
    Verify JWT refresh token
    """
    if not refresh_token:
        raise TokenExceptions.token_is_missing()

    try:
        payload = jwt.decode(refresh_token, settings.refresh_secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise TokenExceptions.invalid_payload()
        
        data = {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "username": payload.get("username")
        }
        access_token = create_access_token(data)
        new_refresh_token = create_refresh_token(data)
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token
        }
    
    except ExpiredSignatureError:
        raise TokenExceptions.expired_token()

    except JWTError:
        raise TokenExceptions.token_exception()


def create_verifcation_token(data: dict) -> str :
    """
    Generate JWT Email Verification - Reset token
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.verification_token_expire_minutes)
    issued_at = datetime.now(timezone.utc)
    to_encode.update({"exp": expire, "iat": issued_at})

    encoded_jwt = jwt.encode(to_encode, settings.verification_secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_verification_token(verification_token: str) -> str:
    """
    Verify JWT verification token
    """
    if not verification_token:
        raise TokenExceptions.token_is_missing()

    try:
        payload = jwt.decode(verification_token, settings.verification_secret_key, algorithms=[settings.algorithm],)
        user_id: str = payload.get('sub')
        if not user_id:
            raise TokenExceptions.invalid_payload()

        return user_id

    except ExpiredSignatureError:
        raise TokenExceptions.expired_token()
    except JWTError:
        raise TokenExceptions.token_exception()
    

def verify_reset_token(verification_token: str) -> str:
    """
    Verify JWT reset token
    """
    if not verification_token:
        raise TokenExceptions.token_is_missing()
    
    try:
        payload = jwt.decode(verification_token, settings.verification_secret_key, algorithms=[settings.algorithm],)
        print(payload)
        email: str = payload.get('sub')
        if not email:
            raise TokenExceptions.invalid_payload()

        return email

    except ExpiredSignatureError:
        raise TokenExceptions.expired_token()
    except JWTError:
        raise TokenExceptions.token_exception()



