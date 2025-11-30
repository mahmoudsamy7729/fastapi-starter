from typing import Annotated
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from src.config import settings


engine = create_async_engine(settings.database_url, echo=True)


async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)




Base = declarative_base()


async def get_db():
    async with async_session() as session:
        yield session


db_dependency = Annotated[AsyncSession, Depends(get_db)]



# ---------------------------
# SYNC (Celery)
# ---------------------------
sync_engine = create_engine(
    settings.sync_database_url,
    future=True,
    echo=False,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_sync_session():
    """Used ONLY inside Celery tasks."""
    db = SyncSessionLocal()
    try:
        return db
    finally:
        db.close()