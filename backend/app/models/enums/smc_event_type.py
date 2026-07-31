from enum import StrEnum


class SMCEventType(StrEnum):
    """Structural concept categories detected by the SMC Engine
    (docs/09_SMC_ENGINE.md, docs/43). Breaker Blocks are not a separate
    type - they're a lifecycle transition of an ORDER_BLOCK_* event (see
    ADR-037), tracked via `SMCEvent.context["is_breaker"]`, not a
    duplicate row."""

    SWING_HH = "swing_hh"
    SWING_HL = "swing_hl"
    SWING_LH = "swing_lh"
    SWING_LL = "swing_ll"
    BOS = "bos"
    CHOCH = "choch"
    ORDER_BLOCK_BULLISH = "order_block_bullish"
    ORDER_BLOCK_BEARISH = "order_block_bearish"
    FAIR_VALUE_GAP_BULLISH = "fair_value_gap_bullish"
    FAIR_VALUE_GAP_BEARISH = "fair_value_gap_bearish"
    LIQUIDITY_EQUAL_HIGHS = "liquidity_equal_highs"
    LIQUIDITY_EQUAL_LOWS = "liquidity_equal_lows"
    LIQUIDITY_SWEEP = "liquidity_sweep"
