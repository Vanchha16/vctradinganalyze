from app.models.asset import Asset
from app.models.enums import MarketType
from app.services.news_sentiment.asset_detector import detect

_EURUSD = Asset(
    symbol="EURUSD",
    name="Euro / US Dollar",
    market_type=MarketType.FOREX,
    base_currency="EUR",
    quote_currency="USD",
)
_XAUUSD = Asset(
    symbol="XAUUSD",
    name="Gold / US Dollar",
    market_type=MarketType.METAL,
    base_currency="XAU",
    quote_currency="USD",
)
_BTCUSD = Asset(
    symbol="BTCUSD",
    name="Bitcoin / US Dollar",
    market_type=MarketType.CRYPTO,
    base_currency="BTC",
    quote_currency="USD",
)
_ALL_ASSETS = [_EURUSD, _XAUUSD, _BTCUSD]


def test_detect_matches_explicit_symbol() -> None:
    matched = detect("EURUSD extends gains", _ALL_ASSETS)
    assert matched == ["EURUSD"]


def test_detect_matches_currency_alias() -> None:
    matched = detect("Gold Prices Slide as Stronger Dollar Weighs on Bullion", _ALL_ASSETS)
    assert "XAUUSD" in matched


def test_detect_matches_crypto_alias() -> None:
    matched = detect("Bitcoin Rallies Past Key Resistance", _ALL_ASSETS)
    assert matched == ["BTCUSD"]


def test_detect_returns_empty_list_for_unrelated_text() -> None:
    matched = detect("Company Reports Quarterly Earnings", _ALL_ASSETS)
    assert matched == []


def test_detect_can_match_multiple_assets() -> None:
    matched = detect("Eurozone GDP Growth Slows as Gold Prices Rise", _ALL_ASSETS)
    assert set(matched) == {"EURUSD", "XAUUSD"}
