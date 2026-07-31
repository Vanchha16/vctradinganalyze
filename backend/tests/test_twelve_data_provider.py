import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.models.enums import Timeframe
from app.services.market_data.exceptions import PermanentProviderError, TransientProviderError
from app.services.market_data.providers.twelve_data import (
    TwelveDataAuthenticationError,
    TwelveDataInvalidSymbolError,
    TwelveDataProvider,
    TwelveDataQuotaExceededError,
)
from tests.market_data_contract import assert_provider_contract

_SUCCESS_BODY = {
    "meta": {
        "symbol": "EUR/USD",
        "interval": "1day",
        "currency": "USD",
        "exchange_timezone": "UTC",
        "exchange": "",
        "type": "Physical Currency",
    },
    "values": [
        {
            "datetime": "2026-01-02",
            "open": "1.10500",
            "high": "1.11000",
            "low": "1.10000",
            "close": "1.10800",
            "volume": "0",
        },
        {
            "datetime": "2026-01-01",
            "open": "1.10000",
            "high": "1.10600",
            "low": "1.09800",
            "close": "1.10500",
            "volume": "0",
        },
    ],
    "status": "ok",
}


def _transport_returning(status_code: int, body: dict[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=json.dumps(body))

    return httpx.MockTransport(handler)


def _provider(transport: httpx.MockTransport) -> TwelveDataProvider:
    return TwelveDataProvider(
        api_key="test-key",
        base_url="https://api.twelvedata.com",
        timeout=5.0,
        transport=transport,
    )


def test_get_candles_parses_successful_response_in_chronological_order() -> None:
    provider = _provider(_transport_returning(200, _SUCCESS_BODY))
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 2, tzinfo=UTC)

    candles = provider.get_candles("EURUSD", Timeframe.D1, start, end)

    assert [c.timestamp for c in candles] == [
        datetime(2026, 1, 1),
        datetime(2026, 1, 2),
    ]
    assert candles[0].open == 1.10000  # oldest value first, per docs/41 §3 ordering
    assert candles[0].volume == 0.0


def test_get_candles_raises_invalid_symbol_error_for_unmappable_symbol() -> None:
    provider = _provider(_transport_returning(200, _SUCCESS_BODY))
    start = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(TwelveDataInvalidSymbolError):
        provider.get_candles("NAS100", Timeframe.D1, start, start)


def test_get_candles_raises_authentication_error_on_401() -> None:
    body = {"code": 401, "message": "Invalid API key", "status": "error"}
    provider = _provider(_transport_returning(401, body))
    start = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(TwelveDataAuthenticationError):
        provider.get_candles("EURUSD", Timeframe.D1, start, start)


def test_get_candles_raises_quota_exceeded_on_429() -> None:
    body = {"code": 429, "message": "API credits exhausted", "status": "error"}
    provider = _provider(_transport_returning(429, body))
    start = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(TwelveDataQuotaExceededError):
        provider.get_candles("EURUSD", Timeframe.D1, start, start)


def test_get_candles_raises_transient_error_on_500() -> None:
    body = {"code": 500, "message": "Internal error", "status": "error"}
    provider = _provider(_transport_returning(500, body))
    start = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(TransientProviderError):
        provider.get_candles("EURUSD", Timeframe.D1, start, start)


def test_get_candles_raises_invalid_symbol_error_on_400() -> None:
    body = {"code": 400, "message": "symbol not found", "status": "error"}
    provider = _provider(_transport_returning(400, body))
    start = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(TwelveDataInvalidSymbolError):
        provider.get_candles("EURUSD", Timeframe.D1, start, start)


def test_get_candles_raises_permanent_error_for_unclassified_status() -> None:
    body = {"code": 418, "message": "teapot", "status": "error"}
    provider = _provider(_transport_returning(418, body))
    start = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(PermanentProviderError):
        provider.get_candles("EURUSD", Timeframe.D1, start, start)


def test_get_candles_raises_transient_error_on_network_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(httpx.MockTransport(handler))
    start = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(TransientProviderError):
        provider.get_candles("EURUSD", Timeframe.D1, start, start)


def test_health_check_returns_true_on_success() -> None:
    provider = _provider(_transport_returning(200, _SUCCESS_BODY))
    assert provider.health_check() is True


def test_health_check_returns_false_on_failure() -> None:
    body = {"code": 401, "message": "Invalid API key", "status": "error"}
    provider = _provider(_transport_returning(401, body))
    assert provider.health_check() is False


def test_health_check_returns_false_on_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    provider = _provider(httpx.MockTransport(handler))
    assert provider.health_check() is False


def test_capabilities_excludes_index_until_symbol_mapping_is_verified() -> None:
    from app.models.enums import MarketType

    provider = _provider(_transport_returning(200, _SUCCESS_BODY))
    caps = provider.capabilities()

    assert MarketType.FOREX in caps.supported_market_types
    assert MarketType.INDEX not in caps.supported_market_types


def test_twelve_data_provider_satisfies_provider_contract() -> None:
    """Reference usage of the shared contract test (docs/40 §10) against a
    mocked transport - no live API call is made."""
    provider = _provider(_transport_returning(200, _SUCCESS_BODY))
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=1)

    assert_provider_contract(provider, "EURUSD", Timeframe.D1, start, end)
