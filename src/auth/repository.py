from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import User, LoginCode

class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def get_by_id(self, user_id: UUID):
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


    async def get_by_email(self, email: str):
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    

    async def get_by_username(self, username: str):
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()


    async def create(self, user: User) -> User: 
        self.db.add(user)
        await self.db.flush()  

        await self.db.commit()
        await self.db.refresh(user)

        return user



    async def update(self, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user
     


class LoginCodeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db


    async def create(self, code: LoginCode):
        self.db.add(code)
        await self.db.commit()


    async def delete(self, user_id : UUID):
        await self.db.execute(
            delete(LoginCode).where(LoginCode.user_id == user_id)
        )
        await self.db.commit()


    async def get_latest_for_user(self, user_id: UUID) -> LoginCode | None:
        result = await self.db.execute(
            select(LoginCode)
            .where(LoginCode.user_id == user_id)
            .order_by(LoginCode.created_at.desc())  # or expires_at.desc()
            .limit(1)
        )
        return result.scalar_one_or_none()