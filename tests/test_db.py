# tests/test_db_connection.py
import pytest
from tests.conftest import TestSessionDB
from sqlalchemy import text

@pytest.mark.asyncio
async def test_async_session():
    async with TestSessionDB() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar()
    assert value == 1

