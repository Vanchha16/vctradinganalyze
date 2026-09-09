"""Provider-name resolution for the economic calendar chain (ADR-150).

`ECONOMIC_CALENDAR_PROVIDERS` is a production config value, so a typo or
an unregistered name is a deployment failure. These pin the names that
are actually settable.
"""

import pytest

from app.config import settings
from app.dependencies.economic_calendar import get_economic_calendar_providers
from app.services.economic_calendar.providers.exceptions import (
    EconomicCalendarProviderConfigurationError,
)


def test_forexfactory_builds_without_an_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """The point of ADR-150: Finnhub's calendar is a paid resource, and
    this feed is public. Requiring a key would have reproduced the
    failure it replaces."""
    monkeypatch.setattr(settings, "economic_calendar_providers", ["forexfactory"])
    monkeypatch.setattr(settings, "economic_api_key", "")

    providers = get_economic_calendar_providers()

    assert [p.name for p in providers] == ["forexfactory"]


def test_finnhub_still_requires_its_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "economic_calendar_providers", ["finnhub"])
    monkeypatch.setattr(settings, "economic_api_key", "")

    with pytest.raises(EconomicCalendarProviderConfigurationError):
        get_economic_calendar_providers()


def test_providers_are_built_in_configured_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """The pipeline tries the chain in order, so this is the fallback
    order, not a set."""
    monkeypatch.setattr(settings, "economic_calendar_providers", ["forexfactory", "mock"])

    assert [p.name for p in get_economic_calendar_providers()] == ["forexfactory", "mock"]


def test_an_unknown_provider_name_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "economic_calendar_providers", ["forex_factory"])

    with pytest.raises(EconomicCalendarProviderConfigurationError):
        get_economic_calendar_providers()
