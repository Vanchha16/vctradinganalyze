"""ADR-183 follow-up - execution safety for smc-ict-crt-v1 signals.

NOT a strategy gate. The frozen v1 rules decide the setup and its entry,
stop and target exactly as before; nothing here changes a formula or
rejects a setup the strategy took. It only asks whether the resulting order
is one a broker can hold at all - a BUY limit with its stop above its entry
is not - and refuses to hand an impossible order to the EA.

The known v1 geometry defect (research/smc_ict_crt_v1/BASELINE_FROZEN.md)
produces such signals in roughly one setup in four. Without this check the
EA sent them, the broker rejected them for invalid stops, and the website's
M1 monitor then recorded a stop-out for a trade that never existed.
"""

from decimal import Decimal

from app.models.enums import SignalType

#: The `signals.strategy` value of every smc-ict-crt-v1 signal. Lives here,
#: in a module with no dependencies, so the EA sync can scope its rule to
#: this strategy without importing the service.
SMC_STRATEGY_NAME = "smc_ict_crt_v1"
#: The `status_reason` prefix every execution-safety rejection carries, so a
#: rejection is never mistaken for a trade outcome or an ordinary cancel.
EXECUTION_SAFETY_REASON = "SMC_SIGNAL_REJECTED_BY_EXECUTION_SAFETY"
#: A live EA's own refusal (broker `order_rejected`, EA `order_skipped`).
EXECUTION_REJECTED_REASON = "SMC_SIGNAL_REJECTED_BY_EXECUTION"


def geometry_violation(
    signal_type: SignalType, entry: Decimal, stop_loss: Decimal, take_profit: Decimal
) -> str | None:
    """Why this order cannot be placed, or None when its geometry is valid.

    BUY:  stop < entry < target.   SELL: target < entry < stop.
    """
    if signal_type is SignalType.BUY:
        if stop_loss >= entry:
            return f"BUY stop {stop_loss} is not below entry {entry}"
        if take_profit <= entry:
            return f"BUY target {take_profit} is not above entry {entry}"
        return None
    if stop_loss <= entry:
        return f"SELL stop {stop_loss} is not above entry {entry}"
    if take_profit >= entry:
        return f"SELL target {take_profit} is not below entry {entry}"
    return None


def is_execution_rejection(status_reason: str | None) -> bool:
    """True for a signal refused by execution safety or by the live EA."""
    if not status_reason:
        return False
    # EXECUTION_SAFETY_REASON begins with EXECUTION_REJECTED_REASON, so one
    # prefix test covers both kinds of refusal.
    return status_reason.startswith((EXECUTION_SAFETY_REASON, EXECUTION_REJECTED_REASON))


__all__ = [
    "SMC_STRATEGY_NAME",
    "EXECUTION_REJECTED_REASON",
    "EXECUTION_SAFETY_REASON",
    "geometry_violation",
    "is_execution_rejection",
]
