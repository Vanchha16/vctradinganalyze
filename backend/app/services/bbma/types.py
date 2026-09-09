"""BBMA domain types (docs/61, ADR-148)."""

from dataclasses import dataclass, field
from enum import StrEnum


class BBMADirection(StrEnum):
    """BBMA is always read as a buy-side or sell-side structure. An
    Extreme SELL forms at the Top BB, an Extreme BUY at the Low BB
    (docs/61 §3.1)."""

    BUY = "buy"
    SELL = "sell"


class BBMASetupKind(StrEnum):
    """The setups in the BBMA cycle (docs/61 §4). Only the three the
    manual calls *entries* are produced by the detector - Extreme, MHV
    and Re-entry (`ENTRY BBMA TYPES`, docs/61 §3). CSM/CSAK/CSK are
    detected as supporting *conditions*, not as entries in their own
    right."""

    EXTREME = "extreme"
    MHV = "mhv"
    RE_ENTRY = "re_entry"


@dataclass(frozen=True, slots=True)
class BBMASetup:
    """One detected BBMA setup on one timeframe.

    `entry_index`/`marked_level` are candle-series indices and prices, so
    a caller can map back to the exact bar - the same discipline ADR-141
    applies to signal monitoring, where pointing at the wrong candle is
    worse than pointing at none.
    """

    kind: BBMASetupKind
    direction: BBMADirection
    #: Index of the candle that *completed* the setup (the retest for
    #: Extreme/MHV, the touching candle for Re-entry). This is the entry
    #: bar.
    entry_index: int
    #: The body extreme of the reverse candle - the level a retest tests
    #: against, and the reference a stop sits beyond. `None` for
    #: Re-entry, which has no reverse candle of its own.
    marked_level: float | None
    #: Where BBMA says to enter: the MA5/10 band (docs/61 §2, "buy only
    #: at MA5/10 Low, sell only at MA5/10 High").
    entry_price: float
    #: Beyond the structure that would invalidate the setup.
    stop_loss: float
    #: Per-setup TP rule (docs/61 §6.2) - mandatory MA5/10-or-MidBB for
    #: Extreme, Low/Top BB for MHV.
    take_profit: float
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BBMAConditions:
    """Supporting structure at the latest bar - the things BBMA reads but
    does not itself enter on."""

    #: Candle closed outside a band: momentum (docs/61 §3.6).
    csm: bool
    #: Candle broke Mid BB (docs/61 §3.7).
    csak: bool
    #: Candle broke outside MA5/10 (docs/61 §3.7).
    csk: bool
    #: All MAs one side of Mid BB and Mid BB one side of EMA50
    #: (docs/61 §3.8).
    zzl: bool
    #: Price vs EMA50 - the trend major (docs/61 §2.2). `None` when EMA50
    #: has insufficient history.
    trend_major: BBMADirection | None
    #: Bollinger Bands expanding vs flat, which decides whether a close
    #: outside the band means momentum or reversal (docs/61 §2).
    bb_expanding: bool


@dataclass(frozen=True, slots=True)
class BBMAResult:
    """The detector's output for one symbol/timeframe."""

    symbol: str
    timeframe: str
    setups: list[BBMASetup]
    conditions: BBMAConditions | None
    warnings: list[str] = field(default_factory=list)

    @property
    def latest(self) -> BBMASetup | None:
        """The most recently completed setup, or `None`. Setups are
        returned oldest-first, matching every other series in this
        project."""
        return self.setups[-1] if self.setups else None


__all__ = [
    "BBMAConditions",
    "BBMADirection",
    "BBMAResult",
    "BBMASetup",
    "BBMASetupKind",
]
