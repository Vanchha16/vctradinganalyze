"""Inbound webhooks (ADR-146).

Currently one route: `POST /webhooks/tradingview/{token}`, which accepts
alerts fired by the Pine scripts in `pinescript/`.

This is the **only unauthenticated-by-session surface in the project
that writes to the database**, so a few properties are deliberate:

- Fail-closed auth on a shared secret in the path
  (`dependencies/webhook_auth.py` explains why the path and not a
  header, and what a bearer URL token does and does not buy).
- An accepted alert is **recorded and notified, never executed**. It
  does not create a `Signal`, does not reach `OrderExecutionService`,
  and cannot place a broker order. Alerts and AI signals stay separate
  all the way down (ADR-146 §Decision).
- The response body reveals nothing about what was stored.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.dependencies.webhook_auth import verify_webhook_token
from app.models.tradingview_alert import TradingViewAlert
from app.repositories.tradingview_alert_repository import TradingViewAlertRepository
from app.schemas.tradingview_alert import (
    TradingViewAlertAcceptedResponse,
    TradingViewAlertRequest,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/tradingview/{token}", response_model=TradingViewAlertAcceptedResponse)
async def receive_tradingview_alert(
    token: str,
    body: TradingViewAlertRequest,
    session: Annotated[Session, Depends(get_db)],
) -> TradingViewAlertAcceptedResponse:
    """Store the alert, then fire a Telegram notification best-effort.

    Order matters: the row is committed *before* the notification is
    enqueued. If the enqueue were first and the commit then failed,
    TradingView would have been told the alert was accepted while
    nothing was kept - and if the notification fails, we still hold the
    record. Delivery failure never fails this response, because
    TradingView retries on a non-2xx and would duplicate an alert we
    already have.
    """
    verify_webhook_token(token)

    repository = TradingViewAlertRepository(session)
    alert = TradingViewAlert(
        symbol=body.symbol,
        exchange=body.exchange,
        timeframe=body.timeframe,
        direction=body.direction,
        score=body.score,
        entry_price=body.entry,
        alert_time=body.time,
        source=body.source,
        # The validated model, not the raw request stream: it is already
        # size-bounded by the field constraints, so an oversized or
        # deeply-nested body cannot be persisted verbatim.
        raw_payload=body.model_dump(mode="json"),
    )
    repository.create(alert)
    repository.commit()

    # Deferred import: avoids a module-level import cycle
    # (telegram_tasks -> celery_app -> workers/__init__), the same
    # pattern `signal_tasks.py`/`signal_monitoring_tasks.py` already use.
    from app.workers.telegram_tasks import enqueue_tradingview_alert_delivery

    enqueue_tradingview_alert_delivery(str(alert.id))

    return TradingViewAlertAcceptedResponse()
