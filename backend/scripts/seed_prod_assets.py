"""Production asset seeding: creates the same EURUSD/XAUUSD/BTCUSD assets as
seed_dev_data.py, but backfills candles via whatever provider chain is
actually configured for this environment (`settings.market_data_providers`)
instead of hardcoding MockMarketDataProvider.

Run in the production environment (real DATABASE_URL, and TWELVE_DATA_API_KEY
if MARKET_DATA_PROVIDERS includes twelve_data):

    python -m scripts.seed_prod_assets

Safe to re-run - `AssetRepository.get_by_symbol` skips assets that already
exist, and `MarketDataService.collect` dedupes candles on
(asset_id, timeframe, timestamp).
"""

from datetime import UTC, datetime, timedelta

from app.database.session import SessionLocal
from app.dependencies.market_data import get_market_data_providers
from app.models.asset import Asset
from app.models.enums import MarketType, Timeframe
from app.repositories.asset_repository import AssetRepository
from app.repositories.price_candle_repository import PriceCandleRepository
from app.services.market_data.candle_validator import CandleValidator
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
            providers=get_market_data_providers(),
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
