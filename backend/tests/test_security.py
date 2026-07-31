import time
import uuid

import jwt
import pytest

from app.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password_roundtrip() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", password_hash) is True


def test_verify_password_rejects_wrong_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("wrong password", password_hash) is False


def test_access_and_refresh_tokens_roundtrip() -> None:
    user_id = uuid.uuid4()

    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)

    access_claims = decode_token(access_token)
    refresh_claims = decode_token(refresh_token)

    assert access_claims["sub"] == str(user_id)
    assert access_claims["type"] == "access"
    assert refresh_claims["sub"] == str(user_id)
    assert refresh_claims["type"] == "refresh"
    assert "jti" in access_claims
    assert "iat" in access_claims
    assert "exp" in access_claims
    assert access_claims["jti"] != refresh_claims["jti"]


def test_decode_token_rejects_expired_token() -> None:
    user_id = uuid.uuid4()
    now = int(time.time())
    expired_payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now - 100,
        "exp": now - 1,
        "jti": str(uuid.uuid4()),
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired_token)


def test_decode_token_rejects_tampered_signature() -> None:
    """Tamper the *first* character of the signature segment, not the
    last. The last base64url character of a JWT can, depending on the
    signature's byte length, only encode padding/insignificant bits - so
    flipping it occasionally round-trips to the same decoded bytes and
    the "tampered" token verifies anyway (a real, reproducible flake
    discovered in Phase 3C, not a one-off). The first character of a
    base64 group always fully determines its leading bits, so tampering
    it is deterministic."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    header, payload, signature = token.split(".")
    tampered_signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    tampered = f"{header}.{payload}.{tampered_signature}"

    with pytest.raises(jwt.InvalidTokenError):
        decode_token(tampered)
