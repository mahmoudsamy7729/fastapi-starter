import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings
from sqlalchemy.pool import NullPool


# Test DB engine & session
test_engine = create_async_engine(settings.test_database_url, echo=True,  poolclass=NullPool)
TestSessionDB = sessionmaker(bind=test_engine, class_=AsyncSession, autoflush=False, autocommit=False)

@pytest.fixture(scope="session", autouse=True)
async def init_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

@pytest.fixture(scope="session", autouse=True)
def override_dependencies():
    async def _get_test_db():
        async with TestSessionDB() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(init_db):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


