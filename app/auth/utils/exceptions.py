from fastapi import HTTPException, status

class UserExceptions:
    """HTTP exceptions related to user actions (login, password, etc)."""

    @staticmethod
    def already_exists() -> HTTPException:
        """User already exists."""
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered",
        )


    @staticmethod
    def invalid_credentials() -> HTTPException:
        """Invalid email or password."""
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The credentials are invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )


    @staticmethod
    def email_not_verified() -> HTTPException:
        """User email is not verified."""
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your email is not verified",
        )
    

    @staticmethod
    def old_password_incorrect() -> HTTPException:
        """Old password is incorrect."""
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Old password isn't correct.",
        )
    

    @staticmethod
    def new_password_same_as_old() -> HTTPException:
        """New password is the same as the old password."""
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as old password."
        )
    

    @staticmethod
    def login_code_expired() -> HTTPException:
        """Login code has expired."""
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login code has expired.",
        )
    

    @staticmethod
    def invalid_login_code() -> HTTPException:
        """Invalid login code."""
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid login code.",
        )
    


class TokenExceptions:
    @staticmethod
    def token_exception() -> HTTPException:
        """Generic token exception."""
        return HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token",
            headers={"WWW-Authenticate": "Bearer"},
        )


    @staticmethod
    def invalid_payload() -> HTTPException:
        """Invalid token payload."""
        return HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )


    @staticmethod
    def token_is_missing() -> HTTPException:
        """Token is missing."""
        return HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail="Token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    

    @staticmethod
    def invalid_token() -> HTTPException:
        """Invalid token."""
        return HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    

    @staticmethod
    def expired_token() -> HTTPException:
        """Expired token."""
        return HTTPException(
            status_code= status.HTTP_401_UNAUTHORIZED,
            detail="Expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

