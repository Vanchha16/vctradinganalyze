from app.services.telegram.keyboards import (
    CALLBACK_SHOW_CHART,
    CALLBACK_SUMMARY_REPORT,
    SHOW_CHART_LABEL,
    SUMMARY_REPORT_LABEL,
    build_main_menu_keyboard,
    build_persistent_menu_keyboard,
)


def test_build_main_menu_keyboard_has_both_buttons_with_matching_callback_data() -> None:
    keyboard = build_main_menu_keyboard()

    buttons = [button for row in keyboard["inline_keyboard"] for button in row]
    callback_values = {button["callback_data"] for button in buttons}

    assert callback_values == {CALLBACK_SUMMARY_REPORT, CALLBACK_SHOW_CHART}
    assert all("text" in button for button in buttons)


def test_build_persistent_menu_keyboard_has_both_labels_and_is_persistent() -> None:
    keyboard = build_persistent_menu_keyboard()

    labels = {button["text"] for row in keyboard["keyboard"] for button in row}

    assert labels == {SUMMARY_REPORT_LABEL, SHOW_CHART_LABEL}
    assert keyboard["is_persistent"] is True
    assert keyboard["resize_keyboard"] is True
