"""Renders a candlestick chart to a PNG image for the Telegram bot's
"Show Chart" button (§13's "send a snapshot image" decision - not a
live-updating chart, which Telegram cannot host in-chat at all).

Styled after TradingView's layout (header with OHLC/change, price axis
on the right, time axis along the bottom, a highlighted current-price
tag) per explicit user request after seeing the plainer first version.
Deliberately still Pillow-only, not matplotlib/mplfinance - this
backend has no pandas/numpy/matplotlib dependency today, and
BACKLOG.md §10 records the production box as genuinely
resource-constrained (911MB RAM, ~1.2GB free disk); Pillow alone is a
~3MB dependency against matplotlib's transitive ~100-150MB. The
tradeoff is a hand-drawn approximation, not pixel-parity with
TradingView - acceptable for an on-demand Telegram snapshot, not for
the web app's own chart (which stays `lightweight-charts`, unaffected
by anything here).
"""

from collections.abc import Callable, Sequence
from decimal import Decimal
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from app.models.price_candle import PriceCandle

_WIDTH = 900
_HEIGHT = 520
_MARGIN_LEFT = 12
_MARGIN_RIGHT = 92
_MARGIN_TOP = 62
_MARGIN_BOTTOM = 34
_BACKGROUND = (255, 255, 255)
_GRID_COLOR = (235, 235, 235)
_AXIS_TEXT_COLOR = (110, 110, 110)
_TEXT_COLOR = (30, 30, 30)
_BULL_COLOR = (38, 166, 91)
_BEAR_COLOR = (214, 57, 60)
_MAX_CANDLES = 60
_PRICE_GRIDLINES = 6
_TIME_LABEL_COUNT = 5


def render_candlestick_chart(
    symbol: str, candles: Sequence[PriceCandle], *, timeframe: str = "M1"
) -> bytes:
    """`candles` must be oldest-first (`PriceCandleRepository.list_recent`'s
    contract) and non-empty - callers check for "no data" separately so
    this function can stay focused on drawing."""
    if not candles:
        raise ValueError("render_candlestick_chart requires at least one candle")

    plotted = list(candles[-_MAX_CANDLES:])
    image = Image.new("RGB", (_WIDTH, _HEIGHT), _BACKGROUND)
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.load_default(size=20)
    stats_font = ImageFont.load_default(size=15)
    axis_font = ImageFont.load_default(size=13)

    plot_left, plot_right = _MARGIN_LEFT, _WIDTH - _MARGIN_RIGHT
    plot_top, plot_bottom = _MARGIN_TOP, _HEIGHT - _MARGIN_BOTTOM

    price_high = max(float(c.high) for c in plotted)
    price_low = min(float(c.low) for c in plotted)
    price_range = price_high - price_low or 1.0

    def y_for(price: float) -> float:
        return plot_bottom - (price - price_low) / price_range * (plot_bottom - plot_top)

    latest = plotted[-1]
    is_bullish = float(latest.close) >= float(latest.open)
    header_color = _BULL_COLOR if is_bullish else _BEAR_COLOR

    _draw_header(draw, symbol, timeframe, plotted, title_font, stats_font)
    _draw_price_gridlines(
        draw, axis_font, plot_left, plot_right, plot_top, plot_bottom, price_low, price_high
    )
    _draw_time_axis(draw, axis_font, plotted, plot_left, plot_right, plot_bottom)
    _draw_candles(draw, plotted, plot_left, plot_right, y_for)
    _draw_current_price_tag(draw, axis_font, plot_right, latest, y_for, header_color)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _draw_header(
    draw: ImageDraw.ImageDraw,
    symbol: str,
    timeframe: str,
    candles: Sequence[PriceCandle],
    title_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    stats_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    latest = candles[-1]
    open_price, high_price = float(latest.open), float(latest.high)
    low_price, close_price = float(latest.low), float(latest.close)

    change_text = "n/a"
    change_color = _TEXT_COLOR
    if len(candles) > 1 and candles[0].close:
        change = close_price - float(candles[0].open)
        change_pct = change / float(candles[0].open) * 100
        change_color = _BULL_COLOR if change >= 0 else _BEAR_COLOR
        change_text = f"{change:+.2f} ({change_pct:+.2f}%)"

    draw.text((_MARGIN_LEFT, 12), f"{symbol}", fill=_TEXT_COLOR, font=title_font)
    title_width = draw.textlength(symbol, font=title_font)
    draw.text(
        (_MARGIN_LEFT + title_width + 12, 16),
        f"· {timeframe} ·",
        fill=_AXIS_TEXT_COLOR,
        font=stats_font,
    )

    stats_text = f"O {open_price:.4f}  H {high_price:.4f}  L {low_price:.4f}  C {close_price:.4f}"
    draw.text((_MARGIN_LEFT, 38), stats_text, fill=_TEXT_COLOR, font=stats_font)
    stats_width = draw.textlength(stats_text, font=stats_font)
    draw.text(
        (_MARGIN_LEFT + stats_width + 16, 38), change_text, fill=change_color, font=stats_font
    )


def _draw_price_gridlines(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    plot_left: float,
    plot_right: float,
    plot_top: float,
    plot_bottom: float,
    price_low: float,
    price_high: float,
) -> None:
    for i in range(_PRICE_GRIDLINES + 1):
        fraction = i / _PRICE_GRIDLINES
        y = plot_bottom - fraction * (plot_bottom - plot_top)
        price = price_low + fraction * (price_high - price_low)
        draw.line([(plot_left, y), (plot_right, y)], fill=_GRID_COLOR, width=1)
        draw.text((plot_right + 6, y - 7), f"{price:.4f}", fill=_AXIS_TEXT_COLOR, font=font)


def _draw_time_axis(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    candles: Sequence[PriceCandle],
    plot_left: float,
    plot_right: float,
    plot_bottom: float,
) -> None:
    count = len(candles)
    if count < 2:
        return
    slot_width = (plot_right - plot_left) / count
    step = max(count // _TIME_LABEL_COUNT, 1)
    for index in range(0, count, step):
        center_x = plot_left + slot_width * (index + 0.5)
        label = candles[index].timestamp.strftime("%H:%M")
        draw.text((center_x - 15, plot_bottom + 8), label, fill=_AXIS_TEXT_COLOR, font=font)


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


def _draw_current_price_tag(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    plot_right: float,
    latest: PriceCandle,
    y_for: Callable[[float], float],
    color: tuple[int, int, int],
) -> None:
    """A filled label at the right edge marking the latest close - the
    one gridline/price a TradingView-style chart always calls out
    distinctly from the rest of the price axis."""
    price = float(latest.close)
    y = y_for(price)
    label = f"{price:.4f}"
    text_width = draw.textlength(label, font=font)
    box = (plot_right + 2, y - 9, plot_right + 10 + text_width, y + 9)
    draw.rectangle(box, fill=color)
    draw.text((plot_right + 6, y - 7), label, fill=(255, 255, 255), font=font)


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
