from app.core.security import hash_password, verify_password
from app.core.jwt_handler import create_access_token, verify_access_token, create_refresh_token, verify_refresh_access_token



def test_password_hash_and_verify():
    password = "StrongPassword123"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_create_and_verify_access_token():
    data = {"sub": "test-user-id"}
    access_token = create_access_token(data)

    payload = verify_access_token(access_token)
    assert payload["sub"] == "test-user-id"


def test_create_verify_refresh_token():
    data = {"sub": "test-user-id"}
    refresh_token = create_refresh_token(data)

    payload = verify_refresh_access_token(refresh_token)
    assert 'access_token' in payload
    assert 'new_refresh_token' in payload




