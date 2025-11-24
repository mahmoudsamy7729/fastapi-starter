import pytest
from uuid import uuid4
from sqlalchemy import select
from src.hashing import hash_password
from tests.conftest import TestSessionDB
from src.auth.models import User, Provider



@pytest.fixture()
async def active_user():
    async with TestSessionDB() as session:

        result = await session.execute(
            select(User).where(User.email == "active@test.com")
        )
        user = result.scalar_one_or_none()
        if user:
            return user

        # 2) لو مش موجود، اعمله create
        hashed = await hash_password("123456")

        user = User(
            id=uuid4(),
            email="active@test.com",
            username="active_user",
            password=hashed,          
            is_active=True,
            is_verified=True,
            provider=Provider.LOCAL,        
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture()
async def disabled_user():
    async with TestSessionDB() as session:
        result = await session.execute(
            select(User).where(User.email == "disabled@test.com")
        )
        user = result.scalar_one_or_none()
        if user:
            return user

        hashed = await hash_password("123456")

        user = User(
            id=uuid4(),
            email="disabled@test.com",
            username="disabled_user",
            password=hashed,
            is_active=False,
            is_verified=False,
            provider=Provider.LOCAL,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user
    

@pytest.fixture
async def logged_in_user(client, active_user):
    response = await client.post("/login", json={
        "email": active_user.email,
        "password": "123456"
    })
    assert response.status_code == 200
    token = response.json()["token"]
    refresh_token = response.cookies.get("refresh_token")

    return {"user": active_user, "token": token, "refresh_token": refresh_token}
