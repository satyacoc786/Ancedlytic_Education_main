import pytest
from backend.auth import hash_password, verify_password, create_access_token, decode_access_token

def test_password_hashing():
    pw = "SuperSecretPassword123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert "$" in hashed
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_token_lifecycle():
    data = {"sub": "admin", "role": "admin"}
    token = create_access_token(data, expires_in_seconds=60)
    assert token is not None

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "admin"
    assert decoded["role"] == "admin"

def test_token_tampering():
    token = create_access_token({"sub": "admin"}, expires_in_seconds=60)
    # Alter token string
    tampered = token[:-4] + "abcd"
    assert decode_access_token(tampered) is None

