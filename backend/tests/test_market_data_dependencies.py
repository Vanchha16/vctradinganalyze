import pytest

from app.config import settings
from app.dependencies.market_data import get_market_data_providers
from app.services.market_data.exceptions import ProviderConfigurationError
from app.services.market_data.providers.rate_limited import RateLimitedProvider


def test_get_market_data_providers_returns_rate_limited_mock() -> None:
    providers = get_market_data_providers()

    assert len(providers) == 1
    assert isinstance(providers[0], RateLimitedProvider)
    assert providers[0].name == "mock"


def test_get_market_data_providers_raises_on_unknown_provider_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "market_data_providers", ["not_a_real_provider"])

    with pytest.raises(ProviderConfigurationError):
        get_market_data_providers()
