"""Historical Performance placeholder (docs/17 §14, docs/49 §9,
ADR-075). No trade-outcomes/backtest dataset exists anywhere in this
project - returns a uniform neutral score for every strategy, mirroring
the Confidence Engine's docs/15 v1.0 §10 deferred-calibration
precedent. Never fabricated as if it were real historical evidence."""

_NEUTRAL_SCORE = 5.0


def score() -> float:
    return _NEUTRAL_SCORE
