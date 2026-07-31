from app.services.analysis_confidence import direction_normalizer
from app.services.analysis_confidence.types import NormalizedDirection
from app.services.smc.types import MarketStructureState
from app.services.technical_analysis.types import TrendDirection


def test_normalize_technical_trend_covers_every_value() -> None:
    assert (
        direction_normalizer.normalize_technical_trend(TrendDirection.BULLISH)
        == NormalizedDirection.BULLISH
    )
    assert (
        direction_normalizer.normalize_technical_trend(TrendDirection.BEARISH)
        == NormalizedDirection.BEARISH
    )
    assert (
        direction_normalizer.normalize_technical_trend(TrendDirection.SIDEWAYS)
        == NormalizedDirection.NEUTRAL
    )


def test_normalize_smc_structure_covers_every_value() -> None:
    assert (
        direction_normalizer.normalize_smc_structure(MarketStructureState.BULLISH)
        == NormalizedDirection.BULLISH
    )
    assert (
        direction_normalizer.normalize_smc_structure(MarketStructureState.BEARISH)
        == NormalizedDirection.BEARISH
    )
    assert (
        direction_normalizer.normalize_smc_structure(MarketStructureState.RANGE)
        == NormalizedDirection.NEUTRAL
    )
    assert (
        direction_normalizer.normalize_smc_structure(MarketStructureState.TRANSITION)
        == NormalizedDirection.NEUTRAL
    )


def test_normalize_regime_direction_covers_every_value() -> None:
    assert (
        direction_normalizer.normalize_regime_direction(TrendDirection.BULLISH)
        == NormalizedDirection.BULLISH
    )
    assert (
        direction_normalizer.normalize_regime_direction(TrendDirection.BEARISH)
        == NormalizedDirection.BEARISH
    )
    assert (
        direction_normalizer.normalize_regime_direction(TrendDirection.SIDEWAYS)
        == NormalizedDirection.NEUTRAL
    )
