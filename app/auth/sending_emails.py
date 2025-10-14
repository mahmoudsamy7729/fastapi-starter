from fastapi_mail import FastMail, MessageSchema, MessageType
from app.core.mail import conf, EmailSchema
from app.core.jwt_handler import create_verifcation_token



class EmailService:
    async def send_verification_email(self, email: EmailSchema, user_id):
        verifcation_token = create_verifcation_token(user_id)
        verify_url = f"http://localhost:8000/auth/verify-email?token={verifcation_token}"
        message = MessageSchema(
            subject="Email Verification",
            recipients=email.email,  # list of recipients
            body=f"Click the link to verify your email: {verify_url}",
            subtype=MessageType.plain  # or "plain"
        )

        fm = FastMail(conf)
        await fm.send_message(message)

async def get_email_service():
    return EmailService()