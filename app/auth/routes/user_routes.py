from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.auth.sending_emails import get_email_service, EmailService
from app.core.database import get_db
from app.core.security import get_current_user
from app.auth.models import User


router = APIRouter(prefix="/user", tags=["User"])


db_dependency = Annotated[AsyncSession, Depends(get_db)]
email_service_dependency = Annotated[EmailService, Depends(get_email_service)]
user_dependency = Annotated[User, Depends(get_current_user)]


@router.get("/protected")
async def protected_route(current_user: user_dependency):
    return {"message": f"Hello {current_user.username}!"}
