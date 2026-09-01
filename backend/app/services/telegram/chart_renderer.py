"""Renders a simple candlestick chart to a PNG image for the Telegram
bot's "Show Chart" button (§13's "send a snapshot image" decision - not
a live-updating chart, which Telegram cannot host in-chat at all).

Deliberately Pillow-only, not matplotlib/mplfinance - this backend has
no pandas/numpy/matplotlib dependency today, and BACKLOG.md §10 records
the production box as genuinely resource-constrained (911MB RAM, ~1.2GB
free disk); Pillow alone is a ~3MB dependency against matplotlib's
transitive ~100-150MB. The tradeoff is a plainer-looking chart than a
real charting library would produce - acceptable for an on-demand
Telegram snapshot, not for the web app's own chart (which stays
`lightweight-charts`, unaffected by anything here).
"""

from collections.abc import Callable, Sequence
from decimal import Decimal
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from app.models.price_candle import PriceCandle

_WIDTH = 900
_HEIGHT = 500
_MARGIN_LEFT = 70
_MARGIN_RIGHT = 20
_MARGIN_TOP = 50
_MARGIN_BOTTOM = 30
_BACKGROUND = (255, 255, 255)
_GRID_COLOR = (230, 230, 230)
_TEXT_COLOR = (30, 30, 30)
_BULL_COLOR = (38, 166, 91)
_BEAR_COLOR = (214, 57, 60)
_MAX_CANDLES = 60


def render_candlestick_chart(symbol: str, candles: Sequence[PriceCandle]) -> bytes:
    """`candles` must be oldest-first (`PriceCandleRepository.list_recent`'s
    contract) and non-empty - callers check for "no data" separately so
    this function can stay focused on drawing."""
    if not candles:
        raise ValueError("render_candlestick_chart requires at least one candle")

    plotted = list(candles[-_MAX_CANDLES:])
    image = Image.new("RGB", (_WIDTH, _HEIGHT), _BACKGROUND)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    plot_left, plot_right = _MARGIN_LEFT, _WIDTH - _MARGIN_RIGHT
    plot_top, plot_bottom = _MARGIN_TOP, _HEIGHT - _MARGIN_BOTTOM

    price_high = max(float(c.high) for c in plotted)
    price_low = min(float(c.low) for c in plotted)
    price_range = price_high - price_low or 1.0

    def y_for(price: float) -> float:
        return plot_bottom - (price - price_low) / price_range * (plot_bottom - plot_top)

    draw.text(
        (_MARGIN_LEFT, 15), f"{symbol} - last {len(plotted)} candles", fill=_TEXT_COLOR, font=font
    )

    _draw_price_gridlines(
        draw, font, plot_left, plot_right, plot_top, plot_bottom, price_low, price_high
    )
    _draw_candles(draw, plotted, plot_left, plot_right, y_for)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _draw_price_gridlines(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    plot_left: float,
    plot_right: float,
    plot_top: float,
    plot_bottom: float,
    price_low: float,
    price_high: float,
    *,
    line_count: int = 4,
) -> None:
    for i in range(line_count + 1):
        fraction = i / line_count
        y = plot_bottom - fraction * (plot_bottom - plot_top)
        price = price_low + fraction * (price_high - price_low)
        draw.line([(plot_left, y), (plot_right, y)], fill=_GRID_COLOR, width=1)
        draw.text((2, y - 6), f"{price:.4f}", fill=_TEXT_COLOR, font=font)


def _draw_candles(
    draw: ImageDraw.ImageDraw,
    candles: Sequence[PriceCandle],
    plot_left: float,
    plot_right: float,
    y_for: Callable[[float], float],
) -> None:
    count = len(candles)
    slot_width = (plot_right - plot_left) / count
    body_width = max(slot_width * 0.6, 2)

    for index, candle in enumerate(candles):
        center_x = plot_left + slot_width * (index + 0.5)
        open_price = float(candle.open)
        close_price = float(candle.close)
        high_price = float(candle.high)
        low_price = float(candle.low)
        is_bullish = close_price >= open_price
        color = _BULL_COLOR if is_bullish else _BEAR_COLOR

        draw.line(
            [(center_x, y_for(high_price)), (center_x, y_for(low_price))], fill=color, width=1
        )

        body_top = y_for(max(open_price, close_price))
        body_bottom = y_for(min(open_price, close_price))
        if body_bottom - body_top < 1:
            body_bottom = body_top + 1
        draw.rectangle(
            [center_x - body_width / 2, body_top, center_x + body_width / 2, body_bottom],
            fill=color,
        )


def format_current_price_caption(symbol: str, candles: Sequence[PriceCandle]) -> str:
    """Plain-text caption accompanying the chart photo - not
    MarkdownV2/escaped, since `sendPhoto`'s `caption` is sent as plain
    text here (no formatting needs it)."""
    latest = candles[-1]
    change_text = ""
    if len(candles) > 1 and candles[0].close:
        change_pct = (
            (Decimal(latest.close) - Decimal(candles[0].close))
            / Decimal(candles[0].close)
            * Decimal(100)
        )
        change_text = f" ({change_pct:+.2f}%)"
    return f"{symbol}: {latest.close}{change_text}"


__all__ = ["format_current_price_caption", "render_candlestick_chart"]
