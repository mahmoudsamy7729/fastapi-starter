from fastapi_mail import FastMail, MessageSchema, MessageType
from app.core.mail import conf, EmailSchema
from app.core.config import settings
from app.core.jwt_handler import create_verifcation_token



class EmailService:
    async def send_verification_email(self, email: EmailSchema, user_id):
        """
        Send verification email after user registers
        """
        verifcation_token = create_verifcation_token(user_id)
        verify_url = f"{settings.app_url}/auth/verify-email?token={verifcation_token}"
        message = MessageSchema(
            subject="Email Verification",
            recipients=email.email,  # list of recipients
            body=f"Click the link to verify your email: {verify_url}",
            subtype=MessageType.plain  # or "plain"
        )

        fm = FastMail(conf)
        await fm.send_message(message)

    async def send_password_reset_email(self, email: EmailSchema, user_email):
        """
        Send password reset link when user forget their password
        """
        verifcation_token = create_verifcation_token(user_email)
        verify_url = f"{settings.app_url}/auth/password-reset?token={verifcation_token}"
        message = MessageSchema(
            subject="Password Reset",
            recipients=email.email,  # list of recipients
            body=f"Click the link to reset your password: {verify_url}",
            subtype=MessageType.plain  # or "plain"
        )

        fm = FastMail(conf)
        await fm.send_message(message)


    async def send_login_code(self, email: EmailSchema, code):
        """
        Send Login Code to be used once expiry date is after 15 min
        """
        message = MessageSchema(
            subject="Login Code",
            recipients=email.email,  # list of recipients
            body=f"Enter the code {code}",
            subtype=MessageType.plain  # or "plain"
        )

        fm = FastMail(conf)
        await fm.send_message(message)

async def get_email_service():
    return EmailService()