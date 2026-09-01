import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from PIL import Image

from app.models.enums import Timeframe
from app.models.price_candle import PriceCandle
from app.services.telegram.chart_renderer import (
    format_current_price_caption,
    render_candlestick_chart,
)


def _candle(*, minutes_ago: int, open_: str, high: str, low: str, close: str) -> PriceCandle:
    return PriceCandle(
        asset_id=uuid.uuid4(),
        timeframe=Timeframe.M1,
        timestamp=datetime.now(UTC) - timedelta(minutes=minutes_ago),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_render_candlestick_chart_produces_a_valid_png() -> None:
    candles = [
        _candle(minutes_ago=2, open_="100", high="102", low="99", close="101"),
        _candle(minutes_ago=1, open_="101", high="103", low="100", close="99"),
        _candle(minutes_ago=0, open_="99", high="100", low="97", close="98"),
    ]

    png_bytes = render_candlestick_chart("EURUSD", candles)

    image = Image.open(BytesIO(png_bytes))
    assert image.format == "PNG"
    assert image.size[0] > 0 and image.size[1] > 0


def test_render_candlestick_chart_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        render_candlestick_chart("EURUSD", [])


def test_render_candlestick_chart_handles_flat_price_range() -> None:
    """Every candle at the exact same price - high==low for the whole
    window would otherwise divide by zero when scaling to pixel space."""
    candles = [_candle(minutes_ago=0, open_="100", high="100", low="100", close="100")]

    png_bytes = render_candlestick_chart("EURUSD", candles)

    assert Image.open(BytesIO(png_bytes)).format == "PNG"


def test_format_current_price_caption_includes_change_percent() -> None:
    candles = [
        _candle(minutes_ago=1, open_="100", high="100", low="100", close="100"),
        _candle(minutes_ago=0, open_="100", high="102", low="100", close="102"),
    ]

    caption = format_current_price_caption("EURUSD", candles)

    assert "EURUSD" in caption
    assert "102" in caption
    assert "+2.00%" in caption


def test_format_current_price_caption_single_candle_has_no_change() -> None:
    candles = [_candle(minutes_ago=0, open_="100", high="101", low="99", close="100")]

    caption = format_current_price_caption("EURUSD", candles)

    assert caption == "EURUSD: 100"
