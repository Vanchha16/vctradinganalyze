"""ADR-183 - shadow run: what smc-ict-crt-v1 would have decided on
production's own stored candles. Read-only, offline, writes nothing to
production.

    python scripts/smc_shadow_run.py <dir-with-H4.csv-and-M5.csv> [hours]

The candle CSVs are read-only exports (`epoch,open,high,low,close`). They
are loaded into an in-memory SQLite database, and the production service is
then stepped forward in five-minute ticks exactly as the Celery task would
run it, so the state machine is exercised the way it will run live.
"""

import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.models.price_candle import PriceCandle
from app.models.signal import Signal
from app.models.smc_setup import SmcSetup
from app.repositories.ai_analysis_repository import AIAnalysisRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.repositories.signal_repository import SignalRepository
from app.repositories.smc_setup_repository import SmcSetupRepository
from app.services.smc_crt.service import SmcCrtService

TABLES = [Asset.__table__, AIAnalysis.__table__, Signal.__table__,
          PriceCandle.__table__, SmcSetup.__table__]


def load(session: Session, asset: Asset, path: Path, timeframe: Timeframe) -> int:
    rows = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        epoch, o, h, low, c = line.split(",")[:5]
        session.add(PriceCandle(
            asset_id=asset.id, timeframe=timeframe,
            timestamp=datetime.fromtimestamp(int(epoch), UTC),
            open=Decimal(o), high=Decimal(h), low=Decimal(low), close=Decimal(c),
            volume=Decimal("1"),
        ))
        rows += 1
    session.flush()
    return rows


def main() -> None:
    data = Path(sys.argv[1])
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 120

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=TABLES)
    session = sessionmaker(bind=engine, class_=Session)()
    asset = Asset(symbol="XAUUSD", name="Gold", market_type=MarketType.METAL, is_active=True)
    session.add(asset)
    session.flush()
    n_h4 = load(session, asset, data / "H4.csv", Timeframe.H4)
    n_m5 = load(session, asset, data / "M5.csv", Timeframe.M5)

    candles = PriceCandleRepository(session)
    newest = candles.get_latest(asset.id, Timeframe.M5)
    end = newest.timestamp.replace(tzinfo=UTC)
    start = end - timedelta(hours=hours)
    print(f"H4 rows {n_h4}, M5 rows {n_m5}")
    print(f"stepping {start:%Y-%m-%d %H:%M} -> {end:%Y-%m-%d %H:%M} UTC in 5-minute ticks\n")

    service = SmcCrtService(SmcSetupRepository(session), candles,
                            SignalRepository(session), AIAnalysisRepository(session))
    now = start
    while now <= end:
        service.run(asset, now)
        now += timedelta(minutes=5)

    setups = session.query(SmcSetup).order_by(SmcSetup.anchor_t).all()
    print(f"{'anchor (UTC)':<17} {'dir':<4} {'state':<20} {'reason':<24} "
          f"{'entry':>9} {'stop':>9} {'target':>9} {'RR':>6}")
    for s in setups:
        print(f"{s.anchor_t:%Y-%m-%d %H:%M}  {s.direction or '-':<4} {str(s.state):<20} "
              f"{(s.reason or '')[:24]:<24} {s.entry or 0:>9.2f} {s.stop_loss or 0:>9.2f} "
              f"{s.take_profit or 0:>9.2f} {s.risk_reward or 0:>6.2f}")
    signals = session.query(Signal).all()
    print(f"\nsetups evaluated: {len(setups)} | signals that would have been created: {len(signals)}")
    for sig in signals:
        print(f"  {sig.signal_type.value.upper()} entry {sig.entry_price} stop {sig.stop_loss} "
              f"target {sig.take_profit} RR {sig.risk_reward} status {sig.status.value} "
              f"reason {sig.status_reason}")
    session.rollback()


if __name__ == "__main__":
    main()
