from app.services.risk_management.trade_quality_aggregator import aggregate, trend_quality_score


def test_trend_quality_score_mapping() -> None:
    assert trend_quality_score("weak") == 5.0
    assert trend_quality_score("moderate") == 12.0
    assert trend_quality_score("strong") == 17.0
    assert trend_quality_score("very_strong") == 20.0
    assert trend_quality_score(None) == 0.0


def test_aggregate_full_score() -> None:
    breakdown = aggregate(
        trend_strength="very_strong",
        technical_score=100.0,
        smc_score=100.0,
        risk_penalties=[],
        news_score=10.0,
        economic_score=10.0,
    )
    assert breakdown.total == 100.0


def test_aggregate_risk_component_floored_at_zero() -> None:
    breakdown = aggregate(
        trend_strength="weak",
        technical_score=0.0,
        smc_score=0.0,
        risk_penalties=[-100.0],
        news_score=0.0,
        economic_score=0.0,
    )
    assert breakdown.risk == 0.0
    assert breakdown.total == 5.0  # only trend_quality's WEAK=5 contributes


def test_aggregate_missing_technical_and_smc_contribute_zero() -> None:
    breakdown = aggregate(
        trend_strength=None,
        technical_score=None,
        smc_score=None,
        risk_penalties=[],
        news_score=5.0,
        economic_score=5.0,
    )
    assert breakdown.trend_quality == 0.0
    assert breakdown.technical == 0.0
    assert breakdown.smc == 0.0
    assert breakdown.total == 30.0  # risk=20 default + news=5 + economic=5


def test_aggregate_total_capped_at_100() -> None:
    breakdown = aggregate(
        trend_strength="very_strong",
        technical_score=100.0,
        smc_score=100.0,
        risk_penalties=[10.0],  # a positive "penalty" shouldn't push risk above 20
        news_score=10.0,
        economic_score=10.0,
    )
    assert breakdown.total == 100.0
