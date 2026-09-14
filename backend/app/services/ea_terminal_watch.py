"""Which Telegram alerts an EA terminal needs right now (ADR-170).

Pure - no DB or I/O. `workers/ea_tasks.py` loads the tokens, sends the
messages and only then writes the new `*_alerted_at` values, so an alert whose
send failed is decided again - and retried - on the next run.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.config import settings
from app.models.ea_token import EaToken
from app.services.risk_management import session_classifier
from app.services.risk_management.types import MarketSession
from app.utils.time import as_aware_utc


class TerminalAlert(StrEnum):
    OFFLINE = "offline"
    BACK_ONLINE = "back_online"
    LOSS_LIMIT = "loss_limit"


@dataclass(frozen=True, slots=True)
class WatchDecision:
    alerts: tuple[TerminalAlert, ...]
    #: What the token's alert markers should become once `alerts` are sent.
    offline_alerted_at: datetime | None
    loss_limit_alerted_at: datetime | None

    def changes(self, token: EaToken) -> bool:
        return (self.offline_alerted_at, self.loss_limit_alerted_at) != (
            token.offline_alerted_at,
            token.loss_limit_alerted_at,
        )


def market_open(now: datetime) -> bool:
    """Gold trades Sunday 22:00 - Friday 22:00 UTC. A terminal that stops over
    the weekend has nothing to miss, so it is reported when the market reopens."""
    return session_classifier.classify(as_aware_utc(now)) is not MarketSession.CLOSED


def decide(token: EaToken, now: datetime, *, is_market_open: bool) -> WatchDecision:
    """Each alert is sent once per episode:

    - **offline**: no poll for `ea_offline_alert_minutes` while the market is
      open, and no offline alert sent yet;
    - **back online**: polling again after an offline alert;
    - **loss limit**: the EA reports its daily loss limit reached, and no alert
      sent for it yet. The marker clears silently once the block lifts, so the
      next blocked day alerts again.
    """
    alerts: list[TerminalAlert] = []
    offline_alerted_at = token.offline_alerted_at
    loss_limit_alerted_at = token.loss_limit_alerted_at

    if token.last_used_at is not None:
        silence = as_aware_utc(now) - as_aware_utc(token.last_used_at)
        offline = silence >= timedelta(minutes=settings.ea_offline_alert_minutes)
        if offline and offline_alerted_at is None and is_market_open:
            alerts.append(TerminalAlert.OFFLINE)
            offline_alerted_at = now
        elif not offline and offline_alerted_at is not None:
            alerts.append(TerminalAlert.BACK_ONLINE)
            offline_alerted_at = None

    if token.effective_loss_blocked is True and loss_limit_alerted_at is None:
        alerts.append(TerminalAlert.LOSS_LIMIT)
        loss_limit_alerted_at = now
    elif token.effective_loss_blocked is not True and loss_limit_alerted_at is not None:
        loss_limit_alerted_at = None

    return WatchDecision(
        alerts=tuple(alerts),
        offline_alerted_at=offline_alerted_at,
        loss_limit_alerted_at=loss_limit_alerted_at,
    )


__all__ = ["TerminalAlert", "WatchDecision", "decide", "market_open"]
