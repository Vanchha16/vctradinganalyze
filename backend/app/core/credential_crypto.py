"""Symmetric encryption for stored API credentials (ADR-156).

Fernet (AES-128-CBC + HMAC-SHA256, from `cryptography`) rather than a
hand-rolled scheme: it is authenticated, so a tampered ciphertext fails
loudly instead of decrypting to garbage that would then be sent to a
vendor as an API key.

**What this does and does not protect.** The master key lives in
`CREDENTIAL_ENCRYPTION_KEY` in the environment, so this defends against a
leaked database dump - `~/deploy_backups` accumulates one per deploy -
or against read access to Postgres. It does NOT defend against someone
who already has the server, since they hold the master key too. That is
the honest boundary and the reason ADR-156 does not claim more.
"""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.exceptions import AppException


class CredentialEncryptionError(AppException):
    """The master key is missing, malformed, or cannot decrypt a value."""

    status_code = 500
    error_code = "credential_encryption_error"


def is_configured() -> bool:
    """Whether credential storage is usable at all.

    Checked before any read/write path so the failure is "this feature is
    not set up" rather than a stack trace deep inside `cryptography`.
    """
    return bool(settings.credential_encryption_key)


def _cipher() -> Fernet:
    if not settings.credential_encryption_key:
        raise CredentialEncryptionError(
            "CREDENTIAL_ENCRYPTION_KEY is not set - credential storage is disabled."
        )
    try:
        return Fernet(settings.credential_encryption_key.encode())
    except (ValueError, TypeError) as exc:
        raise CredentialEncryptionError(
            "CREDENTIAL_ENCRYPTION_KEY is not a valid Fernet key "
            "(generate one with `Fernet.generate_key()`)."
        ) from exc


def encrypt(plaintext: str) -> str:
    return str(_cipher().encrypt(plaintext.encode()).decode())


def decrypt(ciphertext: str) -> str:
    """Raises rather than returning a fallback.

    A silently-wrong key would be sent to a vendor and produce a confusing
    401 far from the real cause - a rotated master key, or a row copied
    between environments.
    """
    try:
        return str(_cipher().decrypt(ciphertext.encode()).decode())
    except InvalidToken as exc:
        raise CredentialEncryptionError(
            "Stored credential could not be decrypted - CREDENTIAL_ENCRYPTION_KEY "
            "has probably changed since it was written."
        ) from exc


def hint_for(plaintext: str) -> str:
    """The tail shown in the UI so an operator can tell one key from
    another. Short keys are masked entirely rather than mostly revealed."""
    return plaintext[-4:] if len(plaintext) >= 12 else "****"


__all__ = ["CredentialEncryptionError", "decrypt", "encrypt", "hint_for", "is_configured"]
