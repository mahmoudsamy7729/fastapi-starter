from datetime import datetime
from fastapi_mail import FastMail, MessageSchema, MessageType
from src.utils import conf
from src.config import settings
import logging

logger = logging.getLogger(__name__)

class Emails:
    @staticmethod
    async def send_subscription_email(subscription: dict):
        message = MessageSchema(
            subject="Subscription Confirmation",
            recipients=[subscription["user"]["email"]],  # list of recipients # type: ignore
            template_body={
                "plan": subscription["plan"]["name"], "start_date": subscription["start_date"],
                "price": subscription["price"],
                "end_date": subscription["end_date"] if subscription["end_date"] else "N/A", 
                "user_name": subscription["user"]["username"], 
                "dashboard_url": settings.app_url,
                "app_name": settings.app_name, "expires_in": settings.validation_token_expire,
                "app_url": settings.app_url,
                "support_email": "support@fast_api.com", "company_address": "1234 Street, City, Country",
                "year": datetime.now().year
                },
            subtype=MessageType.html
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name="subscribe_email.html")


    @staticmethod
    async def send_subscription_update_email(subscription: dict):
        # Fallbacks
        end_date = subscription.get("end_date") or "N/A"
        next_billing_date = subscription.get("next_billing_date") or end_date
        email_type = subscription.get("email_type") or "Activated"

        message = MessageSchema(
            subject=f"Subscription {email_type}",  # e.g. "Subscription Activated" / "Subscription Renewed"
            recipients=[subscription["user"]["email"]],  # type: ignore
            template_body={
                "plan": subscription["plan"]["name"],
                "price": subscription["price"],
                "start_date": subscription["start_date"],
                "end_date": end_date,
                "next_billing_date": next_billing_date,

                "user_name": subscription["user"]["username"],

                "dashboard_url": settings.app_url,
                "app_name": settings.app_name,
                "app_url": settings.app_url,

                "support_email": "support@fast_api.com",
                "company_address": "1234 Street, City, Country",
                "year": datetime.now().year,

                # Used in header & title: "Subscription {{email_type}}"
                "email_type": email_type,
            },
            subtype=MessageType.html,
        )

        fm = FastMail(conf)
        await fm.send_message(message, template_name="update_subscribe_email.html")
