from uuid import UUID
from datetime import datetime, timezone, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from src.models import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def get_by_jti(self, jti: str) -> RefreshToken:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.jti == jti)
        )
        return result.scalar_one_or_none()


    async def create(self, refresh_token: RefreshToken) -> RefreshToken:
        self.db.add(refresh_token)
        await self.db.commit()
        await self.db.refresh(refresh_token)
        return refresh_token
    

    async def update(self, refresh_token: RefreshToken, **kwargs):
        for key, value in kwargs.items():
            setattr(refresh_token, key, value)

        await self.db.commit()
        await self.db.refresh(refresh_token)


    async def revoke_all_for_user(self, user_id: UUID):
        await self.db.execute(
            delete(RefreshToken)
            .where(
                RefreshToken.user_id == user_id
            )
        )
        await self.db.commit()