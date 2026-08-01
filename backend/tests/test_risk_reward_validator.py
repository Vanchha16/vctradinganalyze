from decimal import Decimal

from app.services.risk_management.risk_reward_validator import validate


def test_validate_below_minimum_is_flagged() -> None:
    result = validate(Decimal("1.1000"), Decimal("1.0950"), Decimal("1.1050"))
    assert result.risk_reward == 1.0
    assert result.below_minimum is True


def test_validate_at_minimum_is_not_flagged() -> None:
    result = validate(Decimal("1.1000"), Decimal("1.0950"), Decimal("1.1100"))
    assert result.risk_reward == 2.0
    assert result.below_minimum is False


def test_validate_above_minimum() -> None:
    result = validate(Decimal("1.1000"), Decimal("1.0950"), Decimal("1.1150"))
    assert result.risk_reward == 3.0
    assert result.below_minimum is False


def test_validate_zero_risk_is_flagged() -> None:
    result = validate(Decimal("1.1000"), Decimal("1.1000"), Decimal("1.1100"))
    assert result.below_minimum is True
