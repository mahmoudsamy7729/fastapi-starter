# conftest.py
import pytest
from httpx import AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.database import get_db
from src.main import app 
from src.config import settings

# DB setup
test_engine = create_async_engine(settings.test_database_url, poolclass=NullPool)
TestSessionDB = sessionmaker(bind=test_engine, class_=AsyncSession, autoflush=False, autocommit=False, expire_on_commit=False)

@pytest.fixture(scope="session", autouse=True)
async def init_db():
    from src.database import Base
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

@pytest.fixture(scope="session", autouse=True)
async def override_dependencies():
    async def _get_test_db():
        async with TestSessionDB() as session:
            yield session
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()

@pytest.fixture()
async def client(init_db):
        # ✅ Disable SlowAPI rate limiting during tests
    if hasattr(app.state, "limiter"):
        app.state.limiter.enabled = False

    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
