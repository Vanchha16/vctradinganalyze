from app.services.telegram.keyboards import (
    CALLBACK_SHOW_CHART,
    CALLBACK_SUMMARY_REPORT,
    build_main_menu_keyboard,
)


def test_build_main_menu_keyboard_has_both_buttons_with_matching_callback_data() -> None:
    keyboard = build_main_menu_keyboard()

    buttons = [button for row in keyboard["inline_keyboard"] for button in row]
    callback_values = {button["callback_data"] for button in buttons}

    assert callback_values == {CALLBACK_SUMMARY_REPORT, CALLBACK_SHOW_CHART}
    assert all("text" in button for button in buttons)
