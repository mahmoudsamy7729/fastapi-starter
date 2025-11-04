from fastapi import HTTPException
import pytest


from app.core.security import hash_password, verify_password
from app.core import jwt_handler


def test_password_hash_and_verify():
    password = "strongpassword"
    hashed_password = hash_password(password)

    assert hashed_password != password
    assert verify_password(password, hashed_password) is True
    assert verify_password("wrongpassword", hashed_password) is False


def test_create_and_verify_access_token():
    data = {"sub": "test-user-id"}
    access_token = jwt_handler.create_access_token(data)

    payload = jwt_handler.verify_access_token(access_token)
    assert payload["sub"] == "test-user-id"


def test_invalid_access_token():
    data = {"sub": "test-user-id"}
    access_token = jwt_handler.create_access_token(data)
    invalid_token = access_token + "corrupted"
    with pytest.raises(HTTPException):
        jwt_handler.verify_access_token(invalid_token)


def test_contains_exp_and_sub():
    token = jwt_handler.create_access_token({"sub": "user"})
    payload = jwt_handler.verify_access_token(token)
    assert "exp" in payload
    assert "sub" in payload


def test_create_and_verify_refresh_token():
    data = {"sub": "test-user-id"}
    refresh_token = jwt_handler.create_refresh_token(data)

    payload = jwt_handler.verify_refresh_token(refresh_token)
    assert "access_token" in payload
    

def test_invalid_refresh_token():
    data = {"sub": "test-user-id"}
    refresh_token = jwt_handler.create_refresh_token(data)
    invalid_token = refresh_token + "corrupted"
    with pytest.raises(HTTPException):
        jwt_handler.verify_refresh_token(invalid_token)


def test_create_and_verify_verification_token():
    data = {"sub": "test-user-id"}
    refresh_token = jwt_handler.create_verifcation_token(data)

    payload = jwt_handler.verify_verification_token(refresh_token)
    assert payload == "test-user-id"


def test_invalid_verification_token():
    data = {"sub": "test-user-id"}
    refresh_token = jwt_handler.create_verifcation_token(data)
    invalid_token = refresh_token + "corrupted"
    with pytest.raises(HTTPException):
        jwt_handler.verify_verification_token(invalid_token)


