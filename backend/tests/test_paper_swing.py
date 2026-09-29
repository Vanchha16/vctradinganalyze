"""Swing strategy paper trading (ADR-182).

The rules are a port of the ADR-181 backtest and were checked against it
trade for trade on 2.5 years of exported candles (91/91). These tests pin
the pieces that check cannot: each rule on a hand-built chart, the
no-look-ahead guarantees, the paper record's bookkeeping, and that the
record is only readable by the super admin.
"""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database.base import Base
from app.dependencies import get_current_user, get_db
from app.main import app
from app.models.asset import Asset
from app.models.enums import Timeframe, UserRole
from app.models.paper_swing_trade import PaperSwingTrade
from app.models.price_candle import PriceCandle
from app.models.user import User
from app.repositories.asset_repository import AssetRepository
from app.repositories.paper_swing_trade_repository import PaperSwingTradeRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.paper_swing import rules
from app.services.paper_swing.rules import Bar
from app.services.paper_swing_service import PaperSwingService
from app.workers.paper_swing_tasks import fetch_start

_START = datetime(2026, 1, 1, 1, tzinfo=UTC)

#: (high, low) of the bars after a 60-bar steady climb: a swing high (61),
#: a pullback low (64), the swing high the next pullback comes from (68),
#: that pullback's higher low (71), and three bars that confirm it (74).
_TAIL = [
    (163, 160), (165, 162), (164, 158), (161, 155), (158, 152), (162, 156),
    (166, 160), (171, 165), (200, 170), (173, 166), (170, 163), (168, 160),
    (169, 162), (170, 163), (171, 164),
]  # fmt: skip
_J = 74
_ENTRY = 168.0


def _uptrend_h4() -> list[Bar]:
    # A steady climb has no swing points: every low is above the one before.
    bars = [
        Bar(_START + rules.H4 * i, 101.0 + i, 102.0 + i, 100.0 + i, 101.5 + i) for i in range(60)
    ]
    for n, (high, low) in enumerate(_TAIL):
        i = 60 + n
        close = _ENTRY if i == _J else (high + low) / 2
        bars.append(Bar(_START + rules.H4 * i, (high + low) / 2, high, low, close))
    return bars


def _d1(direction: int, end: datetime, count: int = 70) -> list[Bar]:
    """`count` closed D1 bars ending before `end`, rising (1) or falling (-1)."""
    first = end - rules.D1 * count
    bars = []
    for i in range(count):
        level = 100 + direction * i
        bars.append(Bar(first + rules.D1 * i, level, level + 2, level - 1, level))
    return bars


def _mirror(bars: list[Bar]) -> list[Bar]:
    return [Bar(b.time, 1000 - b.open, 1000 - b.low, 1000 - b.high, 1000 - b.close) for b in bars]


def _signal_time() -> datetime:
    return _START + rules.H4 * (_J + 1)


# --- rules ---------------------------------------------------------------


def test_a_higher_low_pullback_in_a_d1_uptrend_is_a_buy_at_the_swing_levels() -> None:
    h4 = _uptrend_h4()
    [setup] = rules.setups_at(h4, _d1(1, _signal_time()), _J)

    assert setup.direction == "buy"
    assert setup.decision == "taken"
    assert setup.signal_time == _signal_time()
    assert setup.pivot_time == h4[71].time
    assert setup.origin_time == h4[68].time
    assert setup.entry == _ENTRY
    assert setup.target == 200
    atr_now = rules.atr(h4[: _J + 1])[_J]
    assert setup.stop == pytest.approx(160 - 0.1 * atr_now)
    assert setup.risk_reward == pytest.approx((200 - _ENTRY) / (_ENTRY - setup.stop))


def test_the_mirror_image_in_a_d1_downtrend_is_a_sell() -> None:
    h4 = _mirror(_uptrend_h4())
    [setup] = rules.setups_at(h4, _mirror(_d1(1, _signal_time())), _J)

    assert setup.direction == "sell"
    assert setup.decision == "taken"
    assert setup.target == 800
    assert setup.stop > 1000 - 160


def test_no_trade_against_the_d1_trend() -> None:
    assert rules.setups_at(_uptrend_h4(), _d1(-1, _signal_time()), _J) == []


def test_no_trade_without_enough_d1_history() -> None:
    assert rules.setups_at(_uptrend_h4(), _d1(1, _signal_time(), count=40), _J) == []


def test_a_lower_low_breaks_the_structure_and_is_not_a_pullback() -> None:
    h4 = _uptrend_h4()
    h4[71] = Bar(h4[71].time, 150, 168, 150, 159)  # below the earlier swing low (152)
    assert rules.setups_at(h4, _d1(1, _signal_time()), _J) == []


def test_a_setup_below_the_minimum_risk_reward_is_kept_as_rejected() -> None:
    h4 = _uptrend_h4()
    h4[68] = Bar(h4[68].time, 172, 175, 170, 172)  # the target is now only 7 away
    [setup] = rules.setups_at(h4, _d1(1, _signal_time()), _J)

    assert setup.decision == "rr_below_min"
    assert setup.risk_reward < rules.MIN_RISK_REWARD


def test_a_bar_after_the_decision_cannot_change_it() -> None:
    h4 = _uptrend_h4()
    before = rules.setups_at(h4, _d1(1, _signal_time()), _J)
    later = h4 + [Bar(_signal_time(), 168, 300, 1, 150)]
    assert rules.setups_at(later, _d1(1, _signal_time()), _J) == before


def test_closed_bars_drops_the_bar_still_forming() -> None:
    bars = _uptrend_h4()
    now = bars[-1].time + timedelta(hours=2)
    assert rules.closed_bars(bars, rules.H4, now) == bars[:-1]


def test_the_stop_wins_when_one_bar_touches_both_levels() -> None:
    entry_time = _START
    bars = [Bar(entry_time, 100, 120, 80, 100)]
    exit_ = rules.find_exit(
        bars, rules.H4, direction="buy", entry_time=entry_time, stop=90, target=110
    )
    assert exit_ == rules.Exit("loss", 90, entry_time + rules.H4)


def test_a_trade_reaching_neither_level_closes_at_the_market_after_twenty_days() -> None:
    bars = [Bar(_START + rules.H4 * i, 100, 101, 99, 100.5) for i in range(130)]
    exit_ = rules.find_exit(
        bars, rules.H4, direction="sell", entry_time=_START, stop=110, target=90
    )
    assert exit_ is not None
    assert exit_.outcome == "timeout"
    assert exit_.price == 100.5
    assert exit_.time <= _START + rules.MAX_HOLD


def test_an_unfinished_trade_has_no_exit() -> None:
    bars = [Bar(_START, 100, 101, 99, 100)]
    assert (
        rules.find_exit(bars, rules.H4, direction="buy", entry_time=_START, stop=90, target=110)
        is None
    )


def test_average_daily_range_is_the_mean_d1_range_in_pips() -> None:
    d1 = [Bar(_START + rules.D1 * i, 1.1, 1.1020, 1.1000, 1.1) for i in range(14)]
    assert rules.average_daily_range(d1, 0.0001) == pytest.approx(20)
    assert rules.average_daily_range(d1[:13], 0.0001) is None


# --- service ---------------------------------------------------------------

_TABLES = [
    User.__table__,
    Asset.__table__,
    PriceCandle.__table__,
    PaperSwingTrade.__table__,
]


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=_TABLES)
    return engine


def _service(session: Session) -> PaperSwingService:
    return PaperSwingService(
        AssetRepository(session), PriceCandleRepository(session), PaperSwingTradeRepository(session)
    )


def _store(session: Session, asset: Asset, timeframe: Timeframe, bars: list[Bar]) -> None:
    # The fixture's prices are chart-sized; scale them into EURUSD's range so
    # pips come out sensibly (1.00 on the chart = 100 pips).
    for b in bars:
        session.add(
            PriceCandle(
                asset_id=asset.id,
                timeframe=timeframe,
                timestamp=b.time,
                open=Decimal(str(b.open / 100)),
                high=Decimal(str(b.high / 100)),
                low=Decimal(str(b.low / 100)),
                close=Decimal(str(b.close / 100)),
            )
        )
    session.flush()


def _eurusd(session: Session) -> tuple[rules.PairSpec, Asset]:
    pairs = _service(session).ensure_assets()
    return next((spec, asset) for spec, asset in pairs if spec.symbol == "EURUSD")


def test_the_three_pairs_are_created_inactive_so_the_live_pipeline_never_sees_them(
    engine,
) -> None:
    with Session(engine) as session:
        pairs = _service(session).ensure_assets()
        assert [spec.symbol for spec, _ in pairs] == ["EURUSD", "GBPUSD", "USDJPY"]
        assert all(not asset.is_active for _, asset in pairs)
        assert AssetRepository(session).list_active() == []


def test_a_setup_becomes_an_open_paper_trade_with_its_full_record(engine) -> None:
    with Session(engine) as session:
        spec, asset = _eurusd(session)
        _store(session, asset, Timeframe.H4, _uptrend_h4())
        _store(session, asset, Timeframe.D1, _d1(1, _signal_time()))

        result = _service(session).evaluate(spec, asset, _signal_time() + timedelta(minutes=4))

        assert (result.recorded, result.taken, result.closed) == (1, 1, 0)
        [trade] = PaperSwingTradeRepository(session).list_all()
        assert trade.status == "open"
        assert trade.symbol == "EURUSD"
        assert trade.direction == "buy"
        assert trade.strategy_version == rules.STRATEGY_VERSION
        assert trade.entry_price == Decimal("1.68")
        assert trade.take_profit == Decimal("2.00")
        assert trade.risk_reward >= Decimal("2")
        assert trade.adr_pips is not None
        assert trade.closed_at is None


def test_the_trade_closes_at_its_target_net_of_spread_and_swap(engine) -> None:
    with Session(engine) as session:
        spec, asset = _eurusd(session)
        _store(session, asset, Timeframe.H4, _uptrend_h4())
        _store(session, asset, Timeframe.D1, _d1(1, _signal_time()))
        service = _service(session)
        service.evaluate(spec, asset, _signal_time() + timedelta(minutes=4))

        hit = Bar(_signal_time(), 169, 201, 165, 199)
        _store(session, asset, Timeframe.H4, [hit])
        result = service.evaluate(spec, asset, _signal_time() + rules.H4 + timedelta(minutes=4))

        assert result.closed == 1
        [trade] = PaperSwingTradeRepository(session).list_all()
        assert trade.status == "win"
        assert trade.exit_price == Decimal("2.00")
        assert trade.holding_hours == Decimal("4.00")
        gross = (2.00 - 1.68) / 0.0001
        swap = spec.swap_long_pips * 4 / 24
        assert float(trade.result_pips) == pytest.approx(gross + swap - spec.spread_pips, abs=1e-3)
        assert float(trade.result_r) == pytest.approx(
            float(trade.result_pips) / float(trade.risk_pips), abs=1e-3
        )


def test_running_again_records_nothing_twice(engine) -> None:
    with Session(engine) as session:
        spec, asset = _eurusd(session)
        _store(session, asset, Timeframe.H4, _uptrend_h4())
        _store(session, asset, Timeframe.D1, _d1(1, _signal_time()))
        service = _service(session)
        now = _signal_time() + timedelta(minutes=4)

        service.evaluate(spec, asset, now)
        again = service.evaluate(spec, asset, now + timedelta(hours=1))

        assert again.recorded == 0
        assert len(PaperSwingTradeRepository(session).list_all()) == 1


def test_a_second_setup_while_a_trade_is_open_is_recorded_as_skipped(engine) -> None:
    with Session(engine) as session:
        spec, asset = _eurusd(session)
        service = _service(session)
        _store(session, asset, Timeframe.H4, _uptrend_h4())
        _store(session, asset, Timeframe.D1, _d1(1, _signal_time()))
        # An open trade on the same pair, entered a day before the setup.
        blocker = PaperSwingTrade(
            asset_id=asset.id,
            symbol="EURUSD",
            strategy_version=rules.STRATEGY_VERSION,
            setup=rules.SETUP_NAME,
            direction="sell",
            d1_trend="down",
            status="open",
            signal_time=_signal_time() - timedelta(days=1),
            pivot_time=_signal_time() - timedelta(days=2),
            origin_time=_signal_time() - timedelta(days=3),
            pullback_level=Decimal("1"),
            entry_price=Decimal("1"),
            stop_loss=Decimal("5"),
            take_profit=Decimal("0.5"),
            risk_pips=Decimal("40000"),
            reward_pips=Decimal("5000"),
            risk_reward=Decimal("2"),
            atr_h4_pips=Decimal("1"),
            spread_pips=Decimal("0.8"),
        )
        session.add(blocker)
        session.flush()

        service.evaluate(spec, asset, _signal_time() + timedelta(minutes=4))

        statuses = {t.direction: t.status for t in PaperSwingTradeRepository(session).list_all()}
        assert statuses == {"sell": "open", "buy": "skipped"}


def test_statistics_count_closed_trades_and_list_rejections(engine) -> None:
    with Session(engine) as session:
        spec, asset = _eurusd(session)
        _store(session, asset, Timeframe.H4, _uptrend_h4())
        _store(session, asset, Timeframe.D1, _d1(1, _signal_time()))
        service = _service(session)
        service.evaluate(spec, asset, _signal_time() + timedelta(minutes=4))
        _store(session, asset, Timeframe.H4, [Bar(_signal_time(), 169, 201, 165, 199)])
        service.evaluate(spec, asset, _signal_time() + rules.H4 + timedelta(minutes=4))
        session.commit()

        stats = service.statistics(datetime.now(UTC))

        assert stats.overall.trades == 1
        assert stats.overall.wins == 1
        assert stats.overall.win_rate == 100.0
        assert stats.overall.profit_factor is None  # no losing trade yet
        assert stats.by_pair["EURUSD"].trades == 1
        assert stats.by_pair["GBPUSD"].trades == 0
        assert stats.by_direction["buy"].total_r == stats.overall.total_r


# --- API ---------------------------------------------------------------------


@pytest.fixture
def client(engine) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _user(engine, role: UserRole) -> User:
    with Session(engine) as session:
        user = User(
            email=f"{role.value}@example.com",
            username=role.value,
            password_hash=hash_password("Correct-Horse9"),
            role=role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


@pytest.mark.parametrize(
    "path", ["/api/v1/admin/paper-swing/statistics", "/api/v1/admin/paper-swing/trades"]
)
def test_only_the_super_admin_can_read_the_paper_record(engine, client, path: str) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: _user(engine, UserRole.ADMIN)
    assert client.get(path).status_code == 403


def test_the_statistics_show_the_backtest_they_are_judged_against(engine, client) -> None:
    owner = _user(engine, UserRole.SUPER_ADMIN)
    client.app.dependency_overrides[get_current_user] = lambda: owner

    body = client.get("/api/v1/admin/paper-swing/statistics").json()

    assert body["strategy_version"] == rules.STRATEGY_VERSION
    assert body["overall"]["trades"] == 0
    assert body["backtest_reference"]["twelve_data"]["trades"] == 108
    assert body["backtest_reference"]["mt5"]["trades"] == 91
    assert set(body["by_pair"]) == {"EURUSD", "GBPUSD", "USDJPY"}


def test_the_trade_list_returns_the_record(engine, client) -> None:
    with Session(engine) as session:
        spec, asset = _eurusd(session)
        _store(session, asset, Timeframe.H4, _uptrend_h4())
        _store(session, asset, Timeframe.D1, _d1(1, _signal_time()))
        _service(session).evaluate(spec, asset, _signal_time() + timedelta(minutes=4))
        session.commit()
    owner = _user(engine, UserRole.SUPER_ADMIN)
    client.app.dependency_overrides[get_current_user] = lambda: owner

    body = client.get("/api/v1/admin/paper-swing/trades", params={"status": "taken"}).json()

    assert body["total"] == 1
    assert body["items"][0]["symbol"] == "EURUSD"
    assert body["items"][0]["status"] == "open"


# --- when the task fetches -------------------------------------------------


def _hourly(day: datetime) -> list[datetime]:
    return [day + timedelta(hours=h, minutes=4) for h in range(24)]


@pytest.mark.parametrize("first_open_hour", [1, 0], ids=["summer 01:00 grid", "winter 00:00 grid"])
def test_h4_is_fetched_four_minutes_after_each_close_in_either_season(first_open_hour: int) -> None:
    day = datetime(2026, 9, 21, tzinfo=UTC)
    latest = day - timedelta(hours=4 - first_open_hour)  # the bar forming at midnight
    due = []
    for now in _hourly(day):
        if fetch_start(latest, Timeframe.H4, now) is not None:
            due.append(now.hour)
            latest = now - timedelta(minutes=4)  # the provider's new forming bar
    assert due == [h for h in range(24) if h % 4 == first_open_hour]


def test_a_weekend_without_new_bars_still_costs_at_most_six_h4_fetches_a_day() -> None:
    friday_last = datetime(2026, 9, 18, 21, tzinfo=UTC)
    saturday = datetime(2026, 9, 19, tzinfo=UTC)
    due = [now for now in _hourly(saturday) if fetch_start(friday_last, Timeframe.H4, now)]
    assert len(due) == 6


def test_the_switch_between_grids_is_followed_without_a_missed_close() -> None:
    # Last summer-grid bar opened 21:00; the provider's next bar opens 00:00.
    latest = datetime(2026, 10, 30, 21, tzinfo=UTC)
    assert fetch_start(latest, Timeframe.H4, datetime(2026, 10, 31, 1, 4, tzinfo=UTC)) is not None
    latest = datetime(2026, 10, 31, 0, tzinfo=UTC)
    assert fetch_start(latest, Timeframe.H4, datetime(2026, 10, 31, 4, 4, tzinfo=UTC)) is not None
    assert fetch_start(latest, Timeframe.H4, datetime(2026, 10, 31, 5, 4, tzinfo=UTC)) is None


def test_d1_is_fetched_once_just_after_midnight() -> None:
    today = datetime(2026, 9, 21, tzinfo=UTC)
    due = [now.hour for now in _hourly(today) if fetch_start(today - rules.D1, Timeframe.D1, now)]
    assert due == [0]


def test_no_candles_or_a_long_outage_fetches_history_in_one_request() -> None:
    now = datetime(2026, 9, 21, 1, 4, tzinfo=UTC)
    assert fetch_start(None, Timeframe.H4, now) == now - timedelta(days=120)
    assert fetch_start(now - timedelta(days=30), Timeframe.D1, now) == now - timedelta(days=450)
