from app.services.market_regime import transition_analyzer
from app.services.market_regime.types import ExpansionEvidence, ExpansionState, MarketRegimeState
from tests.smc_helpers import make_candles

_STABLE = ExpansionEvidence(state=ExpansionState.STABLE, ratio=1.0)
_EXPANDING = ExpansionEvidence(state=ExpansionState.EXPANSION, ratio=2.0)


def test_shifting_when_price_direction_flips() -> None:
    specs = [
        (100 + i * 0.1, 100 + i * 0.1 + 0.5, 100 + i * 0.1 - 0.5, 100 + i * 0.1) for i in range(20)
    ]
    specs += [
        (102 - i * 0.1, 102 - i * 0.1 + 0.5, 102 - i * 0.1 - 0.5, 102 - i * 0.1) for i in range(20)
    ]
    candles = make_candles(specs)

    evidence = transition_analyzer.analyze(candles, _STABLE)

    assert evidence.shifting is True
    assert evidence.from_hint == MarketRegimeState.TRENDING_BULLISH
    assert evidence.to_hint == MarketRegimeState.TRENDING_BEARISH


def test_shifting_when_volatility_expands_even_without_price_flip() -> None:
    specs = [(100, 100.2, 99.8, 100) for _ in range(30)]
    candles = make_candles(specs)

    evidence = transition_analyzer.analyze(candles, _EXPANDING)

    assert evidence.shifting is True
    assert evidence.confidence >= 50.0


def test_not_shifting_when_stable_and_flat() -> None:
    specs = [(100, 100.2, 99.8, 100) for _ in range(30)]
    candles = make_candles(specs)

    evidence = transition_analyzer.analyze(candles, _STABLE)

    assert evidence.shifting is False


def test_too_few_candles_returns_no_transition() -> None:
    candles = make_candles([(100, 101, 99, 100)])

    evidence = transition_analyzer.analyze(candles, _EXPANDING)

    assert evidence.shifting is False
    assert evidence.confidence == 0.0
