"""Position sizing - the one genuinely new piece of domain logic the EA
Bot spec requires (§5). Converts a risk-validated signal plus real,
live account/symbol data into an order size in MT5 lots.

Deliberately never fabricates a size: every unsafe or undefined input
(non-positive balance, zero stop distance, a computed size below the
broker's own minimum lot) raises `PositionSizingRejectedError` rather
than falling back to a default - same "never fabricate a price"
discipline `candidate_setup_builder.py` follows elsewhere in this
codebase (§1 of the spec).

`account.balance`/`spec.contract_size` are used together, in whatever
native unit the broker itself reports them in (§2/§7 - a Cent account's
balance and its symbol's contract size come from the same MT5 server and
are already mutually consistent; no separate unit conversion is applied
here). This must be verified against the real account's §12 dry-run
output before `EXECUTION_ENABLED` is ever set `true` - not assumed.
"""

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

from app.services.execution.exceptions import PositionSizingRejectedError
from app.services.execution.providers.base import AccountSnapshot, SymbolSpecification


@dataclass(frozen=True, slots=True)
class PositionSizeResult:
    volume: Decimal
    risk_amount: Decimal


def calculate_position_size(
    *,
    account: AccountSnapshot,
    spec: SymbolSpecification,
    entry_price: Decimal,
    stop_loss: Decimal,
    risk_percent: Decimal,
) -> PositionSizeResult:
    balance = Decimal(str(account.balance))
    if balance <= 0:
        raise PositionSizingRejectedError(
            f"non-positive account balance ({balance}), refusing to size a position"
        )

    risk_distance = abs(entry_price - stop_loss)
    if risk_distance <= 0:
        raise PositionSizingRejectedError(
            "zero or invalid stop distance (entry_price == stop_loss), "
            "refusing to size a position"
        )

    contract_size = Decimal(str(spec.contract_size))
    volume_step = Decimal(str(spec.volume_step))
    min_volume = Decimal(str(spec.min_volume))
    max_volume = Decimal(str(spec.max_volume))
    if contract_size <= 0 or volume_step <= 0:
        raise PositionSizingRejectedError(
            f"invalid symbol specification for {spec.symbol!r} "
            f"(contract_size={contract_size}, volume_step={volume_step}), "
            "refusing to size a position"
        )

    risk_amount = balance * (risk_percent / Decimal(100))
    money_at_risk_per_lot = risk_distance * contract_size
    raw_volume = risk_amount / money_at_risk_per_lot

    # Round DOWN to the broker's lot step - never risk more than the
    # configured percentage by rounding up.
    steps = (raw_volume / volume_step).to_integral_value(rounding=ROUND_DOWN)
    volume = steps * volume_step

    if volume < min_volume:
        raise PositionSizingRejectedError(
            f"computed position size ({volume}) is below {spec.symbol!r}'s minimum "
            f"lot ({min_volume}) for the configured {risk_percent}% risk - refusing "
            "to round up to the minimum, since that would exceed the configured risk"
        )

    volume = min(volume, max_volume)
    return PositionSizeResult(volume=volume, risk_amount=risk_amount)


__all__ = ["PositionSizeResult", "calculate_position_size"]
