from uuid import uuid4
from fastapi import HTTPException, status
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError, ExpiredSignatureError
from src.config import settings



def generate_token(data: dict, mins: int, secret_key: str) -> tuple[str, str, datetime]:

    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=mins)
    jti = str(uuid4())
    to_encode.update({"exp": expire, "iat": now, "jti": jti})
    token = jwt.encode(to_encode, secret_key, algorithm=settings.algorithm)
    return token, jti, expire


def verify_token(token: str, secret_key: str) -> dict:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.algorithm])
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if payload.get('sub') is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        return payload

    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")