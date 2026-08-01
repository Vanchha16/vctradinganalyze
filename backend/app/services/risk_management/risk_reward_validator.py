"""Deterministic risk/reward validation (docs/12 §12, docs/48 §6). Pure
arithmetic from the caller-supplied entry/stop/target - below the 1:2
minimum is a hard reject (ADR-068)."""

from dataclasses import dataclass
from decimal import Decimal

_MINIMUM_RR = Decimal("2.0")


@dataclass(frozen=True, slots=True)
class RiskRewardResult:
    risk_reward: float
    below_minimum: bool


def validate(entry_price: Decimal, stop_loss: Decimal, take_profit: Decimal) -> RiskRewardResult:
    reward = abs(take_profit - entry_price)
    risk = abs(entry_price - stop_loss)
    if risk == 0:
        return RiskRewardResult(risk_reward=0.0, below_minimum=True)

    rr = reward / risk
    return RiskRewardResult(risk_reward=float(rr), below_minimum=rr < _MINIMUM_RR)
