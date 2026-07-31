from collections.abc import Callable
from dataclasses import dataclass

from app.indicators.types import IndicatorOutput, OHLCVSeries

IndicatorFunc = Callable[[OHLCVSeries], IndicatorOutput | None]


@dataclass(frozen=True, slots=True)
class IndicatorSpec:
    name: str
    category: str
    func: IndicatorFunc


class IndicatorRegistry:
    """Discovery/registration point for indicator implementations
    (docs/08 §5). Each indicator module registers its own entries at
    import time - `app/indicators/__init__.py` imports every module so
    registration always happens before `list_all()`/`get()` are used."""

    def __init__(self) -> None:
        self._specs: dict[str, IndicatorSpec] = {}

    def register(self, name: str, category: str, func: IndicatorFunc) -> None:
        if name in self._specs:
            raise ValueError(f"Indicator already registered: {name!r}")
        self._specs[name] = IndicatorSpec(name=name, category=category, func=func)

    def get(self, name: str) -> IndicatorSpec:
        return self._specs[name]

    def list_all(self) -> list[IndicatorSpec]:
        return list(self._specs.values())


registry = IndicatorRegistry()
