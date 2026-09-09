"""BBMA (Bollinger Bands + Moving Average) structure detection.

Strategy reference: `docs/61_BBMA_STRATEGY_REFERENCE.md`. Design and the
four invented constants: ADR-148.
"""

from .detector import detect
from .types import (
    BBMAConditions,
    BBMADirection,
    BBMAResult,
    BBMASetup,
    BBMASetupKind,
)

__all__ = [
    "BBMAConditions",
    "BBMADirection",
    "BBMAResult",
    "BBMASetup",
    "BBMASetupKind",
    "detect",
]
