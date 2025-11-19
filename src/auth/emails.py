from datetime import datetime
from fastapi_mail import FastMail, MessageSchema, MessageType
from src.utils import conf
from src.config import settings
from src.jwt import generate_token



class Emails:

    @staticmethod
    async def send_verification_email(email: str, user_id):
        data = {"sub": str(user_id)}
        token = generate_token(data, settings.validation_token_expire, settings.validation_secret_key)
        verify_url = f"{settings.app_url}/verify?token={token}"
        message = MessageSchema(
            subject="Email Verification",
            recipients=[email],  # list of recipients # type: ignore
            template_body={
                "app_name": settings.app_name, "expires_in": settings.validation_token_expire,
                "app_url": settings.app_url, "verification_url": verify_url,
                "support_email": "support@fast_api.com", "company_address": "1234 Street, City, Country",
                "year": datetime.now().year
                },
            subtype=MessageType.html
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name="verify_email.html")


    @staticmethod
    async def send_password_reset_email(email: str, user_id):
        """
        Send password reset link when user forget their password
        """
        data = {"sub": str(user_id)}
        token = generate_token(data, settings.validation_token_expire, settings.validation_secret_key)
        verify_url = f"{settings.app_url}/auth/password-reset?token={token}"
        message = MessageSchema(
            subject="Password Reset",
            recipients=[email],  # list of recipients #type: ignore
            template_body={
                "app_name": settings.app_name, "expires_in": settings.validation_token_expire,
                "app_url": settings.app_url, "reset_url": verify_url,
                "support_email": "support@fast_api.com", "company_address": "1234 Street, City, Country",
                "year": datetime.now().year
                },
            subtype=MessageType.html
        )

        fm = FastMail(conf)
        await fm.send_message(message, template_name="reset_password.html")


    @staticmethod
    async def send_login_code(email: str, code):
        """
        Send Login Code to be used once expiry date is after 15 min
        """
        message = MessageSchema(
            subject="Login Code",
            recipients=[email],  # list of recipients #type: ignore
           template_body={
                "app_name": settings.app_name, "expires_in": settings.validation_token_expire,
                "app_url": settings.app_url, "otp_code": code,
                "support_email": "support@fast_api.com", "company_address": "1234 Street, City, Country",
                "year": datetime.now().year
                },
            subtype=MessageType.html
        )

        fm = FastMail(conf)
        await fm.send_message(message, template_name="otp.html")