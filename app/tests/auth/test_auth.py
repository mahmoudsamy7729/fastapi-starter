import pytest
from fastapi import status

from app.tests.conftest import TestSessionDB
from app.auth.models import User


@pytest.mark.asyncio
async def test_register_login_user_flow(client):
    # Step 1: Register
    user_data = {
        "email": "user@example.com",
        "username": "user_example",
        "password": "strongpassword123",
        "is_active": True,
        "is_verified": True
    }
    response = await client.post("/auth/register", data=user_data)
    assert response.status_code == 201
    assert response.json()["message"] == "Account created successfully, Check email to verify your account"
    user_id = response.json()["user"]["id"]

    async with TestSessionDB() as db:
        user = await db.get(User, user_id)  
        user.is_verified = True
        await db.commit()
        await db.refresh(user)


    # Step 2: Login
    login_data = {
        "email": "user@example.com",
        "password": "strongpassword123"
    }
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    refresh_token = response.cookies['refresh_token']
    token = response.json()["access_token"]
    assert token
    assert refresh_token


    # Step 3: Access protected route
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get("/user/protected", headers=headers)
    assert response.status_code == 200
    assert "Hello" in response.text

    # Step 4: Refresh Token
    response = await client.post("/auth/token/refresh", cookies={"refresh_token": refresh_token})
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" in response.cookies
    assert response.json()["access_token"] != refresh_token


@pytest.mark.asyncio
async def test_refresh_token_missing(client):
    response = await client.post("/auth/token/refresh", json={})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Token is missing"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client):
    response = await client.post("/auth/token/refresh", cookies={"refresh_token": "invalid.token"},)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate refresh token"


@pytest.mark.asyncio
async def test_change_password_success(client, logged_in_user):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}

    response = await client.post("/auth/password/change", json={
        "password": "strongpassword123",
        "new_password": "newstrongpassword1512"
    }, headers = headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully. You can now log in."


@pytest.mark.asyncio
async def test_change_password_failed(client, logged_in_user):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}

    response = await client.post("/auth/password/change", json={
        "password": "wrongPassword",
        "new_password": "newstrongpassword1512"
    }, headers = headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Old password isn't correct."