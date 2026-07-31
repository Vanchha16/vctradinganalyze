from datetime import datetime
from typing import NoReturn

import httpx

from app.models.enums import MarketType, Timeframe
from app.services.market_data.exceptions import (
    PermanentProviderError,
    TransientProviderError,
)
from app.services.market_data.providers.base import ProviderCapabilities, RawCandle
from app.services.market_data.providers.twelve_data_http import (
    TwelveDataHttpClient,
    TwelveDataTransportError,
)
from app.services.market_data.providers.twelve_data_symbols import (
    timeframe_to_interval,
    to_provider_symbol,
)

_CAPABILITIES = ProviderCapabilities(
    supported_timeframes=frozenset(Timeframe),
    supported_market_types=frozenset({MarketType.FOREX, MarketType.METAL, MarketType.CRYPTO}),
    # INDEX is deliberately excluded - docs/41 §4 has no verified index
    # symbol mappings yet; add MarketType.INDEX here once the override
    # table is populated and confirmed against Twelve Data's own catalog.
    max_lookback=None,  # varies by instrument/interval (docs/41) - not a single known value yet
)


class TwelveDataAuthenticationError(PermanentProviderError):
    """Twelve Data rejected the API key (401/403)."""


class TwelveDataQuotaExceededError(TransientProviderError):
    """Twelve Data's own rate limit was hit (429) - distinct from
    `DailyQuotaExceededError`, which `RateLimitedProvider` raises
    proactively before ever reaching Twelve Data (ADR-025)."""


class TwelveDataInvalidSymbolError(PermanentProviderError):
    """The symbol was rejected by Twelve Data, or could not be mapped to a
    Twelve Data symbol in the first place (docs/41 §6)."""


def _parse_datetime(value: str) -> datetime:
    """Twelve Data returns `YYYY-MM-DD HH:MM:SS` for intraday candles and
    `YYYY-MM-DD` for daily+ candles."""
    if len(value) > 10:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return datetime.strptime(value, "%Y-%m-%d")


class TwelveDataProvider:
    """Twelve Data implementation of `MarketDataProvider` (docs/40, docs/41)."""

    name = "twelve_data"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = TwelveDataHttpClient(
            base_url=base_url, api_key=api_key, timeout=timeout, transport=transport
        )

    def get_candles(
        self, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[RawCandle]:
        provider_symbol = to_provider_symbol(symbol)
        if provider_symbol is None:
            raise TwelveDataInvalidSymbolError(
                f"no Twelve Data mapping for canonical symbol {symbol!r} (docs/41 §4/§6)"
            )

        params = {
            "symbol": provider_symbol,
            "interval": timeframe_to_interval(timeframe),
            "start_date": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end_date": end.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone": "UTC",
            "outputsize": "5000",
        }

        try:
            status_code, body = self._http.get("/time_series", params)
        except TwelveDataTransportError as exc:
            raise TransientProviderError(f"twelve_data: {exc}") from exc

        if status_code == 200 and body.get("status") == "ok":
            return self._parse_candles(symbol, timeframe, body)

        self._raise_for_error(status_code, body)

    def _parse_candles(
        self, symbol: str, timeframe: Timeframe, body: dict[str, object]
    ) -> list[RawCandle]:
        values = body.get("values", [])
        if not isinstance(values, list):
            values = []

        candles = [
            RawCandle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=_parse_datetime(row["datetime"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]) if row.get("volume") not in (None, "") else None,
            )
            for row in values
        ]
        # Twelve Data returns newest-first; normalize to chronological
        # order, matching MockMarketDataProvider's convention.
        candles.sort(key=lambda c: c.timestamp)
        return candles

    def _raise_for_error(self, status_code: int, body: dict[str, object]) -> NoReturn:
        message = str(body.get("message", f"HTTP {status_code}"))

        if status_code in (401, 403):
            raise TwelveDataAuthenticationError(f"twelve_data: {message}")
        if status_code == 429:
            raise TwelveDataQuotaExceededError(f"twelve_data: {message}")
        if status_code in (400, 404):
            raise TwelveDataInvalidSymbolError(f"twelve_data: {message}")
        if status_code >= 500:
            raise TransientProviderError(f"twelve_data: {message}")
        raise PermanentProviderError(f"twelve_data: {message}")

    def health_check(self) -> bool:
        try:
            status_code, body = self._http.get(
                "/time_series",
                {"symbol": "EUR/USD", "interval": "1day", "outputsize": "1"},
            )
        except TwelveDataTransportError:
            return False
        return status_code == 200 and body.get("status") == "ok"

    def capabilities(self) -> ProviderCapabilities:
        return _CAPABILITIES
