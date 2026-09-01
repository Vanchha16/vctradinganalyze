"""Inline keyboard for the Telegram bot's main menu (docs/19 §13's
"Inline Buttons"/"Quick Actions" concept, picked up here after docs/57
scoped the initial build down to `/start <code>` only).

Two buttons: Summary Report (today + last 7 days signal recap, plus a
market snapshot) and Show Chart (prompts for a symbol, then replies with
a rendered candlestick image - `chart_renderer.py`). Callback data values
are plain, stable strings `telegram_tasks.py`'s callback-query handler
matches on directly - keep them in sync if either changes.
"""

from typing import Any

CALLBACK_SUMMARY_REPORT = "summary_report"
CALLBACK_SHOW_CHART = "show_chart"


def build_main_menu_keyboard() -> dict[str, Any]:
    """Telegram Bot API `InlineKeyboardMarkup` shape - passed straight
    through as `send_message`'s `reply_markup` JSON body."""
    return {
        "inline_keyboard": [
            [
                {"text": "📊 Summary Report", "callback_data": CALLBACK_SUMMARY_REPORT},
                {"text": "📈 Show Chart", "callback_data": CALLBACK_SHOW_CHART},
            ]
        ]
    }


__all__ = ["CALLBACK_SHOW_CHART", "CALLBACK_SUMMARY_REPORT", "build_main_menu_keyboard"]
