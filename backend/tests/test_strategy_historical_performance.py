from app.services.strategy.historical_performance import score


def test_score_returns_uniform_neutral_value() -> None:
    assert score() == 5.0
