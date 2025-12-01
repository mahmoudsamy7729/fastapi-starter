import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from fastapi import status



@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    with patch("src.auth.emails.Emails.send_verification_email") as mock_send_email:
        payload = {
            "email": "sam@example.com",
            "username": "sam",
            "password": "password123"
        }

        response = await client.post("/register", json=payload)
        assert response.status_code == 201
        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        assert args[0] == "sam@example.com"
        data = response.json()
        assert data["email"] == payload["email"]
        assert data["username"] == payload["username"]


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient, active_user):
    payload = {
        "email": active_user.email,
        "username": "sam2",
        "password": "password123"
    }

    response = await client.post("/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already exists"


@pytest.mark.asyncio
async def test_register_user_duplicate_username(client: AsyncClient, active_user):
    payload = {
        "email": "sam2@example.com",
        "username": active_user.username,
        "password": "password123"
    }

    response = await client.post("/register", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already exists"


@pytest.mark.asyncio
async def test_login_user_success(client: AsyncClient, active_user):
    login_payload = {
        "email": active_user.email,
        "password": "123456"
    }

    response = await client.post("/login", json=login_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "refresh_token" in response.cookies
    assert "token" in data
    assert data["type"] == "Bearer"
    assert data["user"]["email"] == login_payload["email"]


@pytest.mark.asyncio
async def test_login_user_invalid_email(client: AsyncClient):
    login_payload = {
        "email":"wrongemail@example.com",
        "password": "123456"
    }

    response = await client.post("/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid email or password"
    

@pytest.mark.asyncio
async def test_login_user_invalid_password(client: AsyncClient, active_user):
    login_payload = {
        "email": active_user.email,
        "password": "wrongpassword"
    }

    response = await client.post("/login", json=login_payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_user_inactive(client: AsyncClient, disabled_user):
    payload = {
        "email": disabled_user.email,
        "password": "123456"
    }

    response = await client.post("/login", json=payload)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "User is disabled"


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, active_user):
    login_payload = {
        "email": active_user.email,
        "password": "123456"
    }

    login_response = await client.post("/login", json=login_payload)
    assert login_response.status_code == status.HTTP_200_OK

    response = await client.post("/refresh-token")
    assert response.status_code == status.HTTP_200_OK

    refresh_response = await client.post("/refresh-token")
    assert refresh_response.status_code == status.HTTP_200_OK
    data = refresh_response.json()
    assert "token" in data
    assert data["type"] == "Bearer"


@pytest.mark.asyncio
async def test_refresh_token_missing(client: AsyncClient):
    response = await client.post("/refresh-token")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Refresh token is missing."


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    client.cookies.set("refresh_token", "invalidtokenvalue")

    response = await client.post("/refresh-token")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Invalid token"


@pytest.mark.asyncio
async def test_change_password_incorrect_old(client: AsyncClient, logged_in_user):
    change_password_payload = {
        "old_password": "wrongoldpassword",
        "new_password": "newpassword123"
    }
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    response = await client.post("/change-password", json=change_password_payload, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "Old password isn't correct."


@pytest.mark.asyncio
async def test_change_password_success(client: AsyncClient, logged_in_user):
    change_password_payload = {
        "old_password": "123456",
        "new_password": "newpassword123"
    }
    headers = {"Authorization": f"Bearer {logged_in_user['token']}"}
    response = await client.post("/change-password", json=change_password_payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Password has been changed successfuly"