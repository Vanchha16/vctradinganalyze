"""Deterministic indicator calculations, per docs/08_TECHNICAL_ANALYSIS_ENGINE.md
§5 and ADR-006/ADR-007 (indicators are calculated in code, never by AI).

Importing this package registers every indicator module with `registry`
(app/indicators/registry.py) - `IndicatorService`
(app/services/indicator_service.py) discovers indicators through the
registry rather than importing each module directly.
"""

from app.indicators import momentum, trend, trend_strength, volatility, volume  # noqa: F401
from app.indicators.registry import registry
from app.indicators.types import IndicatorOutput, OHLCVSeries

__all__ = ["IndicatorOutput", "OHLCVSeries", "registry"]
