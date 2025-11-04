import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_register_successful(client):
    user_data = {
        "email": "use_r@example.com",
        "username": "use_r_example",
        "password": "strongpassword123"
    }
    response = await client.post("/auth/register", data=user_data)
    assert response.status_code == 201
    assert response.json()["message"] == "Account created successfully, Check email to verify your account"
    assert response.json()["user"]["email"] == "use_r@example.com"
    assert response.json()["user"]["username"] == "use_r_example"


@pytest.mark.asyncio
async def test_register_existing_email(client, verified_user):
    user_data = {
        "email": verified_user.email,
        "username": "new_username",
        "password": "anotherpassword123"
    }
    response = await client.post("/auth/register", data=user_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email or username already registered"


@pytest.mark.asyncio
async def test_register_existing_username(client, verified_user):
    user_data = {
        "email": "new_email@example.com",
        "username": verified_user.username,
        "password": "anotherpassword123"
    }
    response = await client.post("/auth/register", data=user_data)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email or username already registered"


@pytest.mark.asyncio
async def login_user_successful(client, verified_user):
    login_data = {
        "email": verified_user.email,
        "password": "strongpassword123"
    }
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, verified_user):
    login_data = {
        "email": verified_user.email,
        "password": "wrongpassword"
    }
    response = await client.post("/auth/login", json= login_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "The credentials are invalid"


@pytest.mark.asyncio
async def test_login_unverified_email(client):
    user_data = {
        "email": "use_r@example.com",
        "username": "use_r_example",
        "password": "strongpassword123"
    }
    response = await client.post("/auth/register", data=user_data)

    login_data = {
        "email": user_data["email"],
        "password": user_data["password"]
    }
    response = await client.post("/auth/login", json=login_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Your email is not verified"


@pytest.mark.asyncio
async def test_refresh_token_successful(client, logged_in_user):
    response = await client.post("/auth/token/refresh")
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_refresh_token_missing(client):
    response = await client.post("/auth/token/refresh")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Token is missing"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client, logged_in_user):
    # Manually corrupt the refresh token cookie
    client.cookies.set("refresh_token", "invalidtoken")

    response = await client.post("/auth/token/refresh")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Could not validate token"


@pytest.mark.asyncio
async def test_change_password_success(client, logged_in_user):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    response = await client.post("/users/password/change", json={
        "password": "strongpassword123",
        "new_password": "newstrongpassword1512"
    }, headers = headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Password changed successfully. You can now log in."


@pytest.mark.asyncio
async def test_change_password_failed(client, logged_in_user):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    response = await client.post("/users/password/change", json={
        "password": "wrongPassword",
        "new_password": "newstrongpassword1512"
    }, headers = headers)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Old password isn't correct."


@pytest.mark.asyncio
async def test_change_password_new_same_as_old(client, logged_in_user):
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    response = await client.post("/users/password/change", json={
        "password": "strongpassword123",
        "new_password": "strongpassword123"
    }, headers = headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "New password cannot be the same as old password."


