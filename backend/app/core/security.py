import hashlib
import secrets
import string
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings

_password_hasher = PasswordHasher()

TokenType = Literal["access", "refresh"]

_TEMP_PASSWORD_LENGTH = 20
_TEMP_PASSWORD_SPECIAL = "!@#$%^&*()-_=+"


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def generate_temporary_password() -> str:
    """Cryptographically secure, always policy-compliant (docs/23 §7)
    temporary password for admin-created/reset accounts (Phase 8, docs/59
    §6.2/§11). One character from each required class is picked explicitly
    so the result always satisfies `UserService`'s upper/lower/digit/special
    policy by construction, rather than generating random bytes and hoping -
    `secrets.token_urlsafe`'s alphabet has no uppercase-vs-digit guarantee.
    """
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(_TEMP_PASSWORD_SPECIAL),
    ]
    pool = string.ascii_uppercase + string.ascii_lowercase + string.digits + _TEMP_PASSWORD_SPECIAL
    remaining = [secrets.choice(pool) for _ in range(_TEMP_PASSWORD_LENGTH - len(required))]
    password_chars = required + remaining
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _create_token(user_id: uuid.UUID, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, "access", timedelta(minutes=settings.jwt_access_expire_minutes))


def create_refresh_token(user_id: uuid.UUID) -> str:
    return _create_token(user_id, "refresh", timedelta(days=settings.jwt_refresh_expire_days))


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def hash_token(token: str) -> str:
    """Deterministically hash a refresh token for storage/lookup (see ADR-023).

    Unlike password hashing, refresh tokens must be looked up by exact match,
    which rules out Argon2id's salted, verify-only hashes. SHA-256 is
    sufficient here because the token itself is a high-entropy, randomly
    generated JWT rather than a low-entropy user secret.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
