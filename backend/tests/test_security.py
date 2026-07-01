import uuid

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    uid = uuid.uuid4()
    token = create_access_token(uid)
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == str(uid)
    assert payload["type"] == "access"


def test_token_type_enforced():
    token = create_refresh_token(uuid.uuid4())
    # decoding a refresh token as an access token must fail
    with pytest.raises(JWTError):
        decode_token(token, expected_type="access")


def test_tampered_token_rejected():
    token = create_access_token(uuid.uuid4())
    with pytest.raises(JWTError):
        decode_token(token + "tamper", expected_type="access")
