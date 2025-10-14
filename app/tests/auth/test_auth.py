import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_register_login_user_flow(client):
    # Step 1: Register
    user_data = {
        "email": "user@example.com",
        "username": "user_example",
        "password": "strongpassword123",
        "is_active": True
    }
    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    assert response.json()["message"] == "Account created successfully, Check email to verify your account"


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
    response = await client.get("/auth/protected", headers=headers)
    assert response.status_code == 200
    assert "Hello" in response.text

    # Step 4: Refresh Token
    response = await client.post("/auth/refresh", cookies={"refresh_token": refresh_token})
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" in response.cookies
    assert response.json()["access_token"] != refresh_token


async def test_refresh_token_missing(client):
    response = await client.post("/auth/refresh", json={})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Token is missing"


async def test_refresh_token_invalid(client):
    response = await client.post("/auth/refresh", cookies={"refresh_token": "invalid.token"},)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate refresh token"


