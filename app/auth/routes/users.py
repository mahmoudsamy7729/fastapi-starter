from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
import httpx
from fastapi import FastAPI, Request, HTTPException

from app.auth.services.email import get_email_service, EmailService
from app.core.database import get_db
from app.core.security import get_current_user
from app.auth.models import User


router = APIRouter(prefix="/user", tags=["User"])


db_dependency = Annotated[AsyncSession, Depends(get_db)]
email_service_dependency = Annotated[EmailService, Depends(get_email_service)]
user_dependency = Annotated[User, Depends(get_current_user)]


N8N_WEBHOOK_URL = "http://localhost:5678/webhook/3cb0a74d-ef37-4f75-a1cd-f7172e84c2a4/chat"


@router.get("/protected")
async def protected_route(current_user: user_dependency):
    return {"message": f"Hello {current_user.username}!"}


# @router.post("/api/chat")
# async def proxy_chat(request: Request):
    host = request.headers.get("host")
    if host != "http://localhost:3000":
        raise HTTPException(status_code=403, detail="Forbidden origin")
    try:
        
        user_input = await request.json()
        

        async with httpx.AsyncClient() as client:
            response = await client.post(
                N8N_WEBHOOK_URL,
                json={
                    "user_input": user_input,
                    "jwt": "signed_token"
                    },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Basic c2FteToxNTEy"
                         },
                timeout=120
            )

        # Make sure you return the exact format n8n sends back
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=500, detail="Invalid response from n8n")

    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Server Error")