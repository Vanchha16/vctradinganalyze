"""Keyboards for the Telegram bot's main menu (docs/19 §13's "Inline
Buttons"/"Quick Actions" concept, picked up here after docs/57 scoped
the initial build down to `/start <code>` only).

Two actions: Summary Report (today + last 7 days signal recap, plus a
market snapshot) and Show Chart (prompts for a symbol, then replies with
a rendered candlestick image - `chart_renderer.py`).

Two different Telegram keyboard types back these, used at different
points by `telegram_tasks.py`:

- `build_main_menu_keyboard` - an inline keyboard attached to one
  message. Tapping it sends a `callback_query` update carrying
  `CALLBACK_SUMMARY_REPORT`/`CALLBACK_SHOW_CHART`. Scrolls away with
  chat history like any other message's attachment.
- `build_persistent_menu_keyboard` - a reply keyboard docked above the
  compose box (`resize_keyboard`/`is_persistent`), which stays visible
  across every later message until a client explicitly removes it.
  Tapping a button here sends its **label text** back as an ordinary
  text message, not a callback_query - `telegram_tasks.py` matches on
  `SUMMARY_REPORT_LABEL`/`SHOW_CHART_LABEL` exactly. Keep the emoji/text
  identical between the label constants and this keyboard if either
  changes, or the match breaks silently.
"""

from typing import Any

CALLBACK_SUMMARY_REPORT = "summary_report"
CALLBACK_SHOW_CHART = "show_chart"

SUMMARY_REPORT_LABEL = "📊 Summary Report"
SHOW_CHART_LABEL = "📈 Show Chart"


def build_main_menu_keyboard() -> dict[str, Any]:
    """Telegram Bot API `InlineKeyboardMarkup` shape - passed straight
    through as `send_message`'s `reply_markup` JSON body."""
    return {
        "inline_keyboard": [
            [
                {"text": SUMMARY_REPORT_LABEL, "callback_data": CALLBACK_SUMMARY_REPORT},
                {"text": SHOW_CHART_LABEL, "callback_data": CALLBACK_SHOW_CHART},
            ]
        ]
    }


def build_persistent_menu_keyboard() -> dict[str, Any]:
    """Telegram Bot API `ReplyKeyboardMarkup` shape, docked above the
    compose box rather than attached to one message."""
    return {
        "keyboard": [[{"text": SUMMARY_REPORT_LABEL}, {"text": SHOW_CHART_LABEL}]],
        "resize_keyboard": True,
        "is_persistent": True,
    }


__all__ = [
    "CALLBACK_SHOW_CHART",
    "CALLBACK_SUMMARY_REPORT",
    "SHOW_CHART_LABEL",
    "SUMMARY_REPORT_LABEL",
    "build_main_menu_keyboard",
    "build_persistent_menu_keyboard",
]
