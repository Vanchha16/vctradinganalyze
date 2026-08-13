"""§5's "reject, don't guess" rule for position sizing - every unsafe
input must raise `PositionSizingRejectedError`, never fall back to a
guessed size. Real-money system, heaviest unit-test coverage in the EA
Bot spec (§8)."""

from decimal import Decimal

import pytest

from app.services.execution.exceptions import PositionSizingRejectedError
from app.services.execution.position_sizing import calculate_position_size
from app.services.execution.providers.base import AccountSnapshot, SymbolSpecification

_ACCOUNT = AccountSnapshot(balance=100_000.0, equity=100_000.0, currency="USC")
_SPEC = SymbolSpecification(
    symbol="XAUUSDc",
    contract_size=100.0,
    volume_step=0.01,
    min_volume=0.01,
    max_volume=100.0,
    tick_size=0.01,
)


def test_computes_volume_within_risk_budget() -> None:
    result = calculate_position_size(
        account=_ACCOUNT,
        spec=_SPEC,
        entry_price=Decimal("4422.00"),
        stop_loss=Decimal("4400.00"),
        risk_percent=Decimal("3"),
    )

    # risk_amount = 100_000 * 0.03 = 3000; risk/lot = 22 * 100 = 2200;
    # 3000/2200 = 1.3636... rounded DOWN to the 0.01 lot step = 1.36.
    assert result.volume == Decimal("1.36")
    assert result.risk_amount == Decimal("3000.000")


def test_rounds_down_never_up_to_avoid_exceeding_risk_budget() -> None:
    result = calculate_position_size(
        account=_ACCOUNT,
        spec=_SPEC,
        entry_price=Decimal("4422.00"),
        stop_loss=Decimal("4400.00"),
        risk_percent=Decimal("3"),
    )
    money_at_risk = result.volume * Decimal("22") * Decimal("100")
    assert money_at_risk <= result.risk_amount


def test_rejects_zero_balance() -> None:
    zero_balance = AccountSnapshot(balance=0.0, equity=0.0, currency="USC")
    with pytest.raises(PositionSizingRejectedError):
        calculate_position_size(
            account=zero_balance,
            spec=_SPEC,
            entry_price=Decimal("4422.00"),
            stop_loss=Decimal("4400.00"),
            risk_percent=Decimal("3"),
        )


def test_rejects_negative_balance() -> None:
    negative_balance = AccountSnapshot(balance=-500.0, equity=-500.0, currency="USC")
    with pytest.raises(PositionSizingRejectedError):
        calculate_position_size(
            account=negative_balance,
            spec=_SPEC,
            entry_price=Decimal("4422.00"),
            stop_loss=Decimal("4400.00"),
            risk_percent=Decimal("3"),
        )


def test_rejects_zero_stop_distance() -> None:
    with pytest.raises(PositionSizingRejectedError):
        calculate_position_size(
            account=_ACCOUNT,
            spec=_SPEC,
            entry_price=Decimal("4422.00"),
            stop_loss=Decimal("4422.00"),
            risk_percent=Decimal("3"),
        )


def test_rejects_invalid_symbol_specification() -> None:
    broken_spec = SymbolSpecification(
        symbol="XAUUSDc", contract_size=0.0, volume_step=0.01, min_volume=0.01, max_volume=100.0,
        tick_size=0.01,
    )
    with pytest.raises(PositionSizingRejectedError):
        calculate_position_size(
            account=_ACCOUNT,
            spec=broken_spec,
            entry_price=Decimal("4422.00"),
            stop_loss=Decimal("4400.00"),
            risk_percent=Decimal("3"),
        )


def test_rejects_when_computed_size_below_broker_minimum_lot() -> None:
    # A tiny account balance with a wide stop distance computes to less
    # than the broker's 0.01 minimum lot - must reject, not round up
    # (rounding up would silently exceed the configured risk budget).
    tiny_account = AccountSnapshot(balance=10.0, equity=10.0, currency="USC")
    with pytest.raises(PositionSizingRejectedError):
        calculate_position_size(
            account=tiny_account,
            spec=_SPEC,
            entry_price=Decimal("4422.00"),
            stop_loss=Decimal("4400.00"),
            risk_percent=Decimal("3"),
        )


def test_clamps_to_broker_maximum_lot() -> None:
    huge_account = AccountSnapshot(balance=100_000_000.0, equity=100_000_000.0, currency="USC")
    result = calculate_position_size(
        account=huge_account,
        spec=_SPEC,
        entry_price=Decimal("4422.00"),
        stop_loss=Decimal("4400.00"),
        risk_percent=Decimal("3"),
    )
    assert result.volume == Decimal(str(_SPEC.max_volume))


def test_cent_account_balance_and_contract_size_used_together_no_manual_conversion() -> None:
    """§2/§7: a Cent account's balance and its symbol's contract size
    come from the same MT5 server and are already mutually consistent -
    this test locks in that no separate unit conversion is applied."""
    result = calculate_position_size(
        account=_ACCOUNT,  # currency="USC" (cents), balance=100_000.0
        spec=_SPEC,
        entry_price=Decimal("4422.00"),
        stop_loss=Decimal("4400.00"),
        risk_percent=Decimal("1"),
    )
    # risk_amount is computed directly off the raw balance figure, with
    # no *100 or /100 conversion applied anywhere.
    assert result.risk_amount == Decimal(str(_ACCOUNT.balance)) * Decimal("0.01")
