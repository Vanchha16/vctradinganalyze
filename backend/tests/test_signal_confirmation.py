"""Draft confirmation on M15 (ADR-166).

What must hold: only a confirmed M15 break in the signal's direction, after
the draft was created and inside its window, confirms it; a setup that
already reached its stop or target is cancelled rather than published late;
an unconfirmed draft is cancelled when the window closes; and publication -
Telegram and the website's live "created" event - happens at confirmation,
never at creation.
"""

import uuid
from collections.abc import Generator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database.base import Base
from app.models.asset import Asset
from app.models.enums import MarketType, SignalStatus, SignalType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.services import signal_confirmation_service
from app.services.signal_confirmation_service import UNCONFIRMED_REASON, ConfirmationOutcome
from app.services.smc.types import BOSEvidence, Direction, SMCAnalysisResult
from app.workers import signal_confirmation_tasks
from tests.analysis_confidence_helpers import make_smc_result

_CREATED = datetime(2026, 9, 11, 9, 3, tzinfo=UTC)
_WINDOW = timedelta(hours=settings.signal_confirmation_window_hours)


def _signal(signal_type: SignalType = SignalType.SELL, asset_id: uuid.UUID | None = None) -> Signal:
    """SELL: entry 4360, stop 4392 above, target 4297 below. BUY mirrors it."""
    is_sell = signal_type is SignalType.SELL
    return Signal(
        analysis_id=uuid.uuid4(),
        asset_id=asset_id or uuid.uuid4(),
        timeframe=Timeframe.H1,
        signal_type=signal_type,
        entry_price=Decimal("4360"),
        stop_loss=Decimal("4392") if is_sell else Decimal("4328"),
        take_profit=Decimal("4297") if is_sell else Decimal("4423"),
        risk_reward=2.0,
        confidence=70.0,
        status=SignalStatus.DRAFT,
        created_at=_CREATED,
    )


def _candle(at: datetime, low: str, high: str, asset_id: uuid.UUID | None = None) -> PriceCandle:
    return PriceCandle(
        asset_id=asset_id or uuid.uuid4(),
        timeframe=Timeframe.M1,
        timestamp=at,
        open=Decimal(low),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(high),
    )


def _break(direction: Direction, at: datetime, *, confirmed: bool = True) -> BOSEvidence:
    return BOSEvidence(
        direction=direction,
        break_price=Decimal("4340.50000000"),
        break_time=at,
        strength=1.0,
        confirmed=confirmed,
    )


def _m15(*breaks: BOSEvidence) -> SMCAnalysisResult:
    return replace(make_smc_result(timeframe=Timeframe.M15), bos=list(breaks))


# --- The rule ---------------------------------------------------------------


def test_a_break_in_the_signals_direction_confirms_it() -> None:
    decision = signal_confirmation_service.evaluate(
        _signal(),
        [],
        _m15(_break(Direction.BEARISH, _CREATED + timedelta(minutes=20))),
        _CREATED + timedelta(minutes=30),
    )

    assert decision.outcome is ConfirmationOutcome.CONFIRMED
    assert decision.reason == "M15 broke structure bearish at 4340.5."


def test_a_buy_needs_a_bullish_break() -> None:
    at = _CREATED + timedelta(minutes=20)
    now = _CREATED + timedelta(minutes=30)

    wrong = signal_confirmation_service.evaluate(
        _signal(SignalType.BUY), [], _m15(_break(Direction.BEARISH, at)), now
    )
    right = signal_confirmation_service.evaluate(
        _signal(SignalType.BUY), [], _m15(_break(Direction.BULLISH, at)), now
    )

    assert wrong.outcome is ConfirmationOutcome.PENDING
    assert right.outcome is ConfirmationOutcome.CONFIRMED


def test_a_break_from_before_the_draft_does_not_confirm_it() -> None:
    """That break is the move the H1 setup was built on, not a confirmation
    that it has started."""
    decision = signal_confirmation_service.evaluate(
        _signal(),
        [],
        _m15(_break(Direction.BEARISH, _CREATED - timedelta(minutes=5))),
        _CREATED + timedelta(minutes=30),
    )

    assert decision.outcome is ConfirmationOutcome.PENDING


def test_an_unconfirmed_break_does_not_confirm_it() -> None:
    decision = signal_confirmation_service.evaluate(
        _signal(),
        [],
        _m15(_break(Direction.BEARISH, _CREATED + timedelta(minutes=20), confirmed=False)),
        _CREATED + timedelta(minutes=30),
    )

    assert decision.outcome is ConfirmationOutcome.PENDING


def test_a_draft_nobody_confirmed_is_cancelled_when_the_window_closes() -> None:
    decision = signal_confirmation_service.evaluate(_signal(), [], _m15(), _CREATED + _WINDOW)

    assert decision.outcome is ConfirmationOutcome.CANCELLED
    assert decision.reason == UNCONFIRMED_REASON


def test_a_break_after_the_window_is_too_late() -> None:
    """Even if the task only gets to run after it - a late worker must not
    publish a stale setup."""
    decision = signal_confirmation_service.evaluate(
        _signal(),
        [],
        _m15(_break(Direction.BEARISH, _CREATED + _WINDOW + timedelta(minutes=10))),
        _CREATED + _WINDOW + timedelta(minutes=15),
    )

    assert decision.outcome is ConfirmationOutcome.CANCELLED


def test_reaching_the_stop_before_confirmation_cancels_it() -> None:
    """The setup failed before anyone was in it - publishing it now would
    send a signal whose stop has already been hit."""
    decision = signal_confirmation_service.evaluate(
        _signal(),
        [_candle(_CREATED + timedelta(minutes=10), "4380", "4393")],
        _m15(_break(Direction.BEARISH, _CREATED + timedelta(minutes=40))),
        _CREATED + timedelta(minutes=45),
    )

    assert decision.outcome is ConfirmationOutcome.CANCELLED
    assert decision.reason == "Price reached the stop loss before M15 confirmed."


def test_reaching_the_target_before_confirmation_cancels_it() -> None:
    decision = signal_confirmation_service.evaluate(
        _signal(),
        [_candle(_CREATED + timedelta(minutes=10), "4296", "4310")],
        _m15(),
        _CREATED + timedelta(minutes=15),
    )

    assert decision.outcome is ConfirmationOutcome.CANCELLED
    assert "take profit" in (decision.reason or "")


def test_reaching_the_target_after_confirmation_still_confirms() -> None:
    """Confirmed at 09:23, target hit at 09:30, task ran at 09:33. That is a
    good signal that moved fast, not a cancelled one."""
    decision = signal_confirmation_service.evaluate(
        _signal(),
        [_candle(_CREATED + timedelta(minutes=27), "4296", "4310")],
        _m15(_break(Direction.BEARISH, _CREATED + timedelta(minutes=20))),
        _CREATED + timedelta(minutes=30),
    )

    assert decision.outcome is ConfirmationOutcome.CONFIRMED


# --- The task ---------------------------------------------------------------


class _FakeSMCEngine:
    def __init__(self, result: SMCAnalysisResult | None) -> None:
        self.result = result
        self.calls: list[tuple[str, Timeframe]] = []

    def analyze(self, asset: Asset, timeframe: Timeframe) -> SMCAnalysisResult:
        self.calls.append((asset.symbol, timeframe))
        assert self.result is not None
        return self.result


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(
        engine, tables=[Asset.__table__, Signal.__table__, PriceCandle.__table__]
    )
    with Session(engine) as session:
        yield session


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    record: dict[str, list[Any]] = {"telegram": [], "created": [], "changed": []}
    monkeypatch.setattr(
        "app.workers.telegram_tasks.enqueue_signal_delivery",
        lambda signal_id: record["telegram"].append(signal_id),
    )
    monkeypatch.setattr(
        "app.services.signal_events.publish_signal_created",
        lambda signal, symbol: record["created"].append((signal.id, symbol)),
    )
    monkeypatch.setattr(
        "app.services.signal_events.publish_signal_status_changed",
        lambda signal: record["changed"].append(signal.id),
    )
    return record


def _asset(session: Session) -> Asset:
    asset = Asset(symbol="XAUUSD", name="Gold", market_type=MarketType.METAL)
    session.add(asset)
    session.commit()
    return asset


def _run(session: Session, engine: _FakeSMCEngine, now: datetime) -> None:
    signal_confirmation_tasks.confirm_pending_signals(
        SignalRepository(session),
        PriceCandleRepository(session),
        AssetRepository(session),
        engine,  # type: ignore[arg-type]
        session,
        now,
    )


def test_a_confirmed_draft_goes_live_and_is_published_then(
    session: Session, published: dict[str, list[Any]]
) -> None:
    asset = _asset(session)
    draft = _signal(asset_id=asset.id)
    session.add(draft)
    session.commit()
    now = _CREATED + timedelta(minutes=30)

    engine = _FakeSMCEngine(_m15(_break(Direction.BEARISH, _CREATED + timedelta(minutes=20))))

    _run(session, engine, now)

    session.refresh(draft)
    assert draft.status is SignalStatus.ACTIVE
    assert draft.confirmed_at is not None
    assert draft.status_reason == "M15 broke structure bearish at 4340.5."
    assert published["telegram"] == [str(draft.id)]
    assert published["created"] == [(draft.id, "XAUUSD")]


def test_confirmation_starts_the_fill_watch_now_not_at_creation(
    session: Session, published: dict[str, list[Any]]
) -> None:
    """Price touching entry while the signal was still a draft was not a fill
    anyone could have had - the monitor must not count it."""
    asset = _asset(session)
    draft = _signal(asset_id=asset.id)
    session.add(draft)
    session.commit()
    now = _CREATED + timedelta(minutes=30)

    engine = _FakeSMCEngine(_m15(_break(Direction.BEARISH, _CREATED + timedelta(minutes=20))))

    _run(session, engine, now)

    session.refresh(draft)
    assert draft.last_monitored_at is not None
    assert draft.last_monitored_at.replace(tzinfo=UTC) == now


def test_a_pending_draft_is_left_alone_and_not_published(
    session: Session, published: dict[str, list[Any]]
) -> None:
    asset = _asset(session)
    draft = _signal(asset_id=asset.id)
    session.add(draft)
    session.commit()

    _run(session, _FakeSMCEngine(_m15()), _CREATED + timedelta(minutes=30))

    session.refresh(draft)
    assert draft.status is SignalStatus.DRAFT
    assert published == {"telegram": [], "created": [], "changed": []}


def test_an_expired_draft_is_cancelled_quietly(
    session: Session, published: dict[str, list[Any]]
) -> None:
    """Cancelled with its reason, and the website told - but no Telegram
    message: nobody was ever told about the draft in the first place."""
    asset = _asset(session)
    draft = _signal(asset_id=asset.id)
    session.add(draft)
    session.commit()

    _run(session, _FakeSMCEngine(_m15()), _CREATED + _WINDOW)

    session.refresh(draft)
    assert draft.status is SignalStatus.CANCELLED
    assert draft.status_reason == UNCONFIRMED_REASON
    assert published["telegram"] == []
    assert published["changed"] == [draft.id]


def test_one_m15_analysis_per_asset_however_many_drafts(
    session: Session, published: dict[str, list[Any]]
) -> None:
    asset = _asset(session)
    session.add_all([_signal(asset_id=asset.id), _signal(asset_id=asset.id)])
    session.commit()
    engine = _FakeSMCEngine(_m15())

    _run(session, engine, _CREATED + timedelta(minutes=30))

    assert engine.calls == [("XAUUSD", Timeframe.M15)]
