import pytest
from app.auth.models import User
from app.tests.conftest import TestSessionDB
from app.auth.services.auth_services import UserService  # your service to create users
from app.auth import schema

@pytest.fixture
async def verified_user():
    """Create and return a verified user for tests"""
    async with TestSessionDB() as db:
        # 1️⃣ Create user data
        user_data = schema.UserCreate(
            email="verified@example.com",
            username="verified_user",
            password="strongpassword123",
            is_active=True
        )

        # 2️⃣ Create the user
        user = await UserService.create_user(db, user_data)

        # 3️⃣ Mark user as verified
        user.is_verified = True
        await db.commit()
        await db.refresh(user)

        # 4️⃣ Return the verified user
        yield user

        await db.delete(user)
        await db.commit()


@pytest.fixture
async def logged_in_user(client, verified_user):
    response = await client.post("/auth/login", json={
        "email": verified_user.email,
        "password": "strongpassword123"
    })
    assert response.status_code == 200
    token = response.json()["access_token"]

    return {"user": verified_user, "token": token}

