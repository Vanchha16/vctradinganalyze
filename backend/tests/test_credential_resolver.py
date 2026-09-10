"""Credential resolution order (ADR-156/157).

The cache holds the *database lookup*, never the resolved value. Caching
the answer pins the `.env` fallback too, so an environment change is
served stale until the TTL expires - and it leaked between tests that
monkeypatch a settings key, which is how the distinction was found.
"""

import pytest
from cryptography.fernet import Fernet

from app.config import settings
from app.services import credential_resolver


@pytest.fixture(autouse=True)
def clean_cache() -> None:
    credential_resolver.invalidate()


def test_falls_back_to_the_environment_when_nothing_is_stored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "env-key-1")

    assert credential_resolver.resolve("openai") == "env-key-1"


def test_an_environment_change_is_visible_immediately_despite_the_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The regression this cache design exists to prevent: with the
    resolved value cached, the second read below returned the first
    value for up to 30 seconds."""
    monkeypatch.setattr(settings, "credential_encryption_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "openai_api_key", "env-key-1")
    assert credential_resolver.resolve("openai") == "env-key-1"

    monkeypatch.setattr(settings, "openai_api_key", "env-key-2")

    assert credential_resolver.resolve("openai") == "env-key-2"


def test_storage_disabled_skips_the_database_entirely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no master key there is nothing to decrypt with, so the
    resolver must not touch the database at all."""
    monkeypatch.setattr(settings, "credential_encryption_key", "")
    monkeypatch.setattr(settings, "twelve_data_api_key", "env-only")

    called = False

    def _fail(name: str) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(credential_resolver, "_read_stored", _fail)

    assert credential_resolver.resolve("twelve_data") == "env-only"
    assert called is False


def test_an_absent_key_resolves_to_empty_rather_than_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Callers already treat an empty key as "provider not configured";
    raising here would turn a configuration gap into a 500."""
    monkeypatch.setattr(settings, "news_api_key", "")

    assert credential_resolver.resolve("news_api") == ""


def test_every_managed_name_has_a_fallback_setting_that_exists() -> None:
    """A typo in the map would silently resolve to "" and look like an
    unconfigured provider rather than a bug."""
    for name, attribute in credential_resolver.FALLBACK_SETTING.items():
        assert hasattr(settings, attribute), f"{name} -> {attribute} is not a Settings field"
