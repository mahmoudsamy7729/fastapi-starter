from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from fastapi import Depends
from typing import Annotated


engine = create_async_engine(settings.database_url, echo=True)



async_session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
)

Base = declarative_base()

from app.users.models import User


async def get_db():
    async with async_session() as session:
        yield session

db_dependency = Annotated[AsyncSession, Depends(get_db)]


        