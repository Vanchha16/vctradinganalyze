"""ADR-183 - the production path must reproduce frozen smc-ict-crt-v1.

Two guarantees:

1. `app/services/smc_crt/rules.py` is byte-for-byte the frozen research
   module. If anyone edits either copy, this fails.
2. On fixtures whose expected outcome is known from the frozen rules, the
   production service reaches the same decision, entry, stop, target and
   R:R.

A mismatch is a defect in the production adapter, never a reason to change
the research result or v1.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.audit_log import AuditLog
from app.models.ea_execution_event import EaExecutionEvent
from app.models.ea_token import EaToken
from app.models.enums import MarketType, SignalStatus, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.models.smc_setup import SmcSetup, SmcSetupState
from app.models.user import User
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_setup_repository import SmcSetupRepository
from app.services.smc_crt import rules
from app.services.smc_crt.service import STRATEGY_NAME, SmcCrtService
from app.utils.time import as_aware_utc

RESEARCH_RULES = (
    Path(__file__).resolve().parents[2] / "research" / "smc_ict_crt_v1" / "rules.py"
)
#: sha256 of the frozen research module, recorded in
#: research/smc_ict_crt_v1/BASELINE_FROZEN.md when v1 was frozen on
#: 2026-09-23. Pinned here so production verifies itself even where the
#: research folder is not checked out.
FROZEN_RULES_SHA256 = "6363cdb63061d6b70ab11e0cbab3c6261d4e0fcc8f94c99791135da66f2c9134"

_TABLES = [
    User.__table__, Asset.__table__, AIAnalysis.__table__, Signal.__table__,
    PriceCandle.__table__, SmcSetup.__table__, EaToken.__table__,
    EaExecutionEvent.__table__, AuditLog.__table__,
]


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=_TABLES)
    factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    with factory() as session:
        yield session


H4 = timedelta(hours=4)
M5 = timedelta(minutes=5)
T0 = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)


def test_production_rules_match_the_frozen_checksum():
    produced = hashlib.sha256(Path(rules.__file__).read_bytes()).hexdigest()
    assert produced == FROZEN_RULES_SHA256, (
        "the production copy of the smc-ict-crt-v1 rules has drifted from the frozen "
        "research module - v1 is immutable, so this is a defect, not an update"
    )


def test_production_rules_are_byte_identical_to_the_research_module():
    if not RESEARCH_RULES.exists():  # research folder is not deployed to production
        pytest.skip("research checkout not present")
    assert hashlib.sha256(RESEARCH_RULES.read_bytes()).hexdigest() == FROZEN_RULES_SHA256


# --- fixture helpers -------------------------------------------------------
def _asset(session) -> Asset:
    asset = Asset(symbol="XAUUSD", name="Gold", market_type=MarketType.METAL, is_active=True)
    session.add(asset)
    session.flush()
    return asset


def _store(session, asset: Asset, timeframe: Timeframe, start: datetime, step, rows):
    for i, (o, h, low, c) in enumerate(rows):
        session.add(PriceCandle(
            asset_id=asset.id, timeframe=timeframe, timestamp=start + step * i,
            open=Decimal(str(o)), high=Decimal(str(h)), low=Decimal(str(low)),
            close=Decimal(str(c)), volume=Decimal("1"),
        ))
    session.flush()


def _service(session) -> SmcCrtService:
    return SmcCrtService(
        SmcSetupRepository(session), PriceCandleRepository(session),
        SignalRepository(session), AIAnalysisRepository(session),
    )


def _flat_h4(n: int, price: float = 100.0):
    """Quiet H4 history: no sweeps, so it produces no candidate of its own."""
    return [(price, price + 1, price - 1, price)] * n


def _buy_fixture():
    """A textbook bullish CRT: anchor, raid below the low closing back inside,
    then an M5 shift up through a confirmed swing high with a gap behind it."""
    h4 = _flat_h4(19)
    h4 += [(100, 101, 88, 100)]            # earlier low at 88: the key level
    h4 += [(100, 130, 90, 105)]            # anchor: CRT 90-130
    h4 += [(105, 106, 88, 100)]            # raid: swept 88, closed back inside
    # 14 quiet bars first so ATR(14) exists and the stop buffer is real;
    # identical bars form no fractal pivot, so they change no decision.
    m5 = [(95, 95.5, 94.5, 95)] * 14
    m5 += [(95, 96, 94, 95), (95, 96, 94, 95),
          (95, 97, 94.5, 96), (96, 98, 95, 97), (97, 99, 96, 98),  # swing high 99
          (98, 98.5, 96, 96.5), (96.5, 97, 95.5, 96),
          (96, 101, 96, 100.5),            # close above 99 -> MSS
          (100.5, 102, 100, 101)]
    return h4, m5


# --- parity fixtures -------------------------------------------------------
def test_buy_fixture_matches_the_frozen_rules_end_to_end(db_session):
    h4_rows, m5_rows = _buy_fixture()
    asset = _asset(db_session)
    h4_start = T0
    _store(db_session, asset, Timeframe.H4, h4_start, H4, h4_rows)
    raid_close = h4_start + H4 * len(h4_rows)
    _store(db_session, asset, Timeframe.M5, raid_close, M5, m5_rows)
    now = raid_close + M5 * (len(m5_rows) + 1)

    # What the frozen research rules say about this data:
    h4 = [rules.Candle(h4_start + H4 * i, *r) for i, r in enumerate(h4_rows)]
    expected = rules.crt_candidate(h4, len(h4) - 1)
    assert expected is not None and expected.direction is rules.Direction.BUY
    assert expected.closed_back_inside is True

    setups = _service(db_session).run(asset, now)
    assert setups, "the production path must evaluate the same raid"
    produced = setups[-1]
    assert produced.direction == "buy"
    assert float(produced.crt_high) == expected.crt_high
    assert float(produced.crt_low) == expected.crt_low
    assert float(produced.raid_extreme) == expected.raid_extreme
    assert produced.state is SmcSetupState.SIGNAL_CREATED, produced.reason
    assert produced.news_status == "NEWS_UNKNOWN"  # never "no news"
    assert produced.key_levels and "88" in produced.key_levels
    assert produced.location == "discount"  # premium/discount recorded, not filtered

    signal = SignalRepository(db_session).get_by_id(produced.signal_id)
    assert signal.strategy == STRATEGY_NAME
    assert signal.status is SignalStatus.ACTIVE  # never DRAFT: no M1 confirmation step
    assert float(signal.take_profit) == expected.crt_high  # TP = opposite CRT boundary
    assert float(signal.stop_loss) < expected.raid_extreme  # stop beyond the raid + buffer
    assert signal.risk_reward >= rules.MIN_RR
    # SQLite drops tzinfo on round-trip; production (Postgres) keeps it.
    assert as_aware_utc(signal.confirmed_at) == as_aware_utc(produced.mss_t)


def test_rejected_setup_keeps_its_real_reason_not_a_generic_wait(db_session):
    """A raid that never closes back inside is recorded with its own reason."""
    h4_rows = _flat_h4(20) + [(100, 110, 90, 105), (95, 96, 85, 87)]
    asset = _asset(db_session)
    _store(db_session, asset, Timeframe.H4, T0, H4, h4_rows)
    now = T0 + H4 * (len(h4_rows) + 1)
    setups = _service(db_session).run(asset, now)
    assert setups[-1].reason == rules.Reason.NO_CLOSE_BACK_INSIDE
    assert setups[-1].state is SmcSetupState.CANCELLED
