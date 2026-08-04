"""One-off local dev seeding: creates a few assets and backfills mock
candles so the developer dashboard has real data to render. Not part of
any migration/CI path - safe to re-run against the local SQLite dev.db.
"""

from datetime import UTC, datetime, timedelta

from app.database.session import SessionLocal
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_data.candle_validator import CandleValidator
from app.services.market_data.providers.mock import MockMarketDataProvider
from app.services.market_data_service import MarketDataService

ASSETS = [
    ("EURUSD", "Euro / US Dollar", MarketType.FOREX, "EUR", "USD"),
    ("XAUUSD", "Gold / US Dollar", MarketType.METAL, "XAU", "USD"),
    ("BTCUSD", "Bitcoin / US Dollar", MarketType.CRYPTO, "BTC", "USD"),
]

TIMEFRAMES = [Timeframe.M15, Timeframe.H1, Timeframe.H4, Timeframe.D1]


def main() -> None:
    session = SessionLocal()
    try:
        asset_repo = AssetRepository(session)
        candle_repo = PriceCandleRepository(session)
        service = MarketDataService(
            providers=[MockMarketDataProvider()],
            candle_validator=CandleValidator(),
            price_candle_repository=candle_repo,
        )

        end = datetime.now(UTC)
        start = end - timedelta(days=90)

        for symbol, name, market_type, base_ccy, quote_ccy in ASSETS:
            asset = asset_repo.get_by_symbol(symbol)
            if asset is None:
                asset = Asset(
                    symbol=symbol,
                    name=name,
                    market_type=market_type,
                    base_currency=base_ccy,
                    quote_currency=quote_ccy,
                    is_active=True,
                )
                session.add(asset)
                session.commit()
                session.refresh(asset)
                print(f"created asset {symbol}")

            for timeframe in TIMEFRAMES:
                result = service.collect(asset, timeframe, start=start, end=end)
                print(f"{symbol} {timeframe.value}: persisted={result.persisted}")

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()
