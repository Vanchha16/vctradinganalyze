# Indicator Reference

Version: 1.0

Status: Canonical reference for every indicator implemented in `app/indicators/` (Phase 3A). Covers the full docs/08_TECHNICAL_ANALYSIS_ENGINE.md §5 list. Does not cover trend detection, technical scoring, or conflict detection (docs/08 §7-11) - that synthesis is Phase 4's Technical Analysis Engine, which consumes the values this document describes.

---

# 1. Conventions Used in This Document

- **Inputs**: which OHLCV series a formula reads (`app/indicators/types.py::OHLCVSeries` - `opens`, `highs`, `lows`, `closes`, `volumes`).
- **Parameters**: the period(s)/multiplier(s) fixed by docs/08 §5 and used by the registered indicator (`app/indicators/registry.py`).
- **Output fields**: `IndicatorResult.value` (the headline number) and `IndicatorResult.context`/`metadata` (secondary values, for multi-output indicators).
- **Warm-up requirement**: the minimum candle count before the indicator produces a value (fewer candles -> the registered function returns `None` and `IndicatorService` skips it - see BACKLOG.md §11).
- **Numerical precision**: all indicator math (`app/indicators/`) operates on Python `float` (IEEE 754 double, ~15-17 significant decimal digits), converted from the `Decimal`-typed `price_candles` columns at the `IndicatorService` boundary. The final `IndicatorResult.value`/`context` are stored as `Numeric(20, 8)` (`Decimal`) - see BACKLOG.md for the documented float-vs-Decimal tradeoff.
- **Registered name**: the string stored in `IndicatorResult.indicator`.

---

# 2. Trend

## EMA (Exponential Moving Average) - `ema_20`, `ema_50`, `ema_100`, `ema_200`

Mathematical definition

```
multiplier = 2 / (period + 1)
EMA[0] = SMA(closes[0:period])
EMA[i] = (close[i] - EMA[i-1]) * multiplier + EMA[i-1]
```

Inputs: `closes`

Parameters: `period` ∈ {20, 50, 100, 200}

Output fields: `value` = latest EMA. No secondary fields.

Warm-up requirement: `period` candles.

Numerical precision: `float`; seeded with a simple average, then recurrence - stable for the periods used here.

External reference/source: standard technical-analysis EMA definition (widely attributed to J. Welles Wilder Jr.'s contemporaries in the 1970s-80s TA literature; no single canonical paper).

---

## SMA (Simple Moving Average) - `sma_200`

Mathematical definition

```
SMA[i] = mean(closes[i-period+1 : i+1])
```

Inputs: `closes`

Parameters: `period` = 200

Output fields: `value` = latest SMA.

Warm-up requirement: 200 candles.

Numerical precision: `float`; arithmetic mean, no compounding error beyond standard float summation.

External reference/source: elementary moving-average definition, universal in TA literature.

---

# 3. Momentum

## RSI (Relative Strength Index, 14) - `rsi_14`

Mathematical definition (Wilder smoothing)

```
delta[i] = close[i] - close[i-1]
gain[i] = max(delta[i], 0); loss[i] = max(-delta[i], 0)
avg_gain[0] = mean(gain[0:period]); avg_loss[0] = mean(loss[0:period])   # seed
avg_gain[i] = (avg_gain[i-1] * (period-1) + gain[i]) / period            # Wilder recurrence
avg_loss[i] = (avg_loss[i-1] * (period-1) + loss[i]) / period
RS = avg_gain / avg_loss
RSI = 100 - (100 / (1 + RS))        # RSI = 100 if avg_loss == 0
```

Inputs: `closes`

Parameters: `period` = 14

Output fields: `value` = latest RSI (range 0-100).

Warm-up requirement: `2 * period` = 28 candles (`period + 1` to seed the gain/loss smoothing, matched again by Stochastic RSI's own windowing - see `app/indicators/momentum.py::rsi_series`).

Numerical precision: `float`; Wilder's recurrence is numerically stable.

External reference/source: J. Welles Wilder Jr., *New Concepts in Technical Trading Systems* (1978).

---

## MACD (12, 26, 9) - `macd`

Mathematical definition

```
MACD_line[i] = EMA(closes, 12)[i] - EMA(closes, 26)[i]
Signal_line = EMA(MACD_line, 9)
Histogram = MACD_line - Signal_line
```

Inputs: `closes`

Parameters: `fast` = 12, `slow` = 26, `signal` = 9

Output fields: `value` = MACD line. `context.signal` = signal line, `context.histogram` = histogram.

Warm-up requirement: `slow + signal - 1` = 34 candles.

Numerical precision: `float`; computed via full EMA series (not just final values) so the signal line's own EMA seed is well-defined - see `app/indicators/momentum.py::macd`.

External reference/source: Gerald Appel, developer of MACD (1970s).

---

## Stochastic RSI (14) - `stoch_rsi_14`

Mathematical definition

```
RSI_series = RSI(closes, period)  # a series, not just the latest value
window = RSI_series[-period:]
StochRSI = (RSI_series[-1] - min(window)) / (max(window) - min(window)) * 100
```

(Returns 0 if `max(window) == min(window)`, e.g. RSI pinned at a ceiling/floor for the whole window.)

Inputs: `closes`

Parameters: `period` = 14

Output fields: `value` = latest Stochastic RSI (range 0-100).

Warm-up requirement: `2 * period` = 28 candles (needs a full RSI series of length `period`, which itself needs `period` candles to begin - see §3 RSI).

Numerical precision: `float`.

External reference/source: Tushar Chande and Stanley Kroll, *The New Technical Trader* (1994).

---

## CCI (Commodity Channel Index, 20) - `cci_20`

Mathematical definition

```
typical_price[i] = (high[i] + low[i] + close[i]) / 3
mean_price = mean(typical_price[-period:])
mean_deviation = mean(|typical_price[j] - mean_price| for j in window)
CCI = (typical_price[-1] - mean_price) / (0.015 * mean_deviation)
```

(Returns 0 if `mean_deviation == 0`, e.g. constant prices.)

Inputs: `highs`, `lows`, `closes`

Parameters: `period` = 20

Output fields: `value` = latest CCI.

Warm-up requirement: 20 candles.

Numerical precision: `float`.

External reference/source: Donald Lambert, *Commodities* magazine (1980).

---

## Momentum (10) - `momentum_10`

Mathematical definition

```
Momentum = close[-1] - close[-1-period]
```

Inputs: `closes`

Parameters: `period` = 10

Output fields: `value` = latest momentum (absolute price change, not a ratio).

Warm-up requirement: `period + 1` = 11 candles.

Numerical precision: `float`; a single subtraction, no accumulated error.

External reference/source: standard TA momentum definition, universal in TA literature.

---

# 4. Volatility

## ATR (Average True Range, 14) - `atr_14`

Mathematical definition (Wilder smoothing)

```
TR[i] = max(high[i]-low[i], |high[i]-close[i-1]|, |low[i]-close[i-1]|)
ATR[0] = mean(TR[0:period])                                # seed
ATR[i] = (ATR[i-1] * (period-1) + TR[i]) / period           # Wilder recurrence
```

Inputs: `highs`, `lows`, `closes`

Parameters: `period` = 14

Output fields: `value` = latest ATR.

Warm-up requirement: `period + 1` = 15 candles (True Range needs a previous close, so the first TR is at index 1).

Numerical precision: `float`.

External reference/source: J. Welles Wilder Jr., *New Concepts in Technical Trading Systems* (1978).

---

## Bollinger Bands (20, 2) - `bollinger_bands_20`

Mathematical definition

```
middle = SMA(closes, period)
std = population_stdev(closes[-period:])
upper = middle + (std_dev_multiplier * std)
lower = middle - (std_dev_multiplier * std)
```

Inputs: `closes`

Parameters: `period` = 20, `std_dev_multiplier` = 2.0

Output fields: `value` = middle band. `context.upper`, `context.lower`.

Warm-up requirement: 20 candles.

Numerical precision: `float`; population (not sample) standard deviation - see `app/indicators/_utils.py::population_stdev`.

External reference/source: John Bollinger, developer of Bollinger Bands (1980s).

---

## Standard Deviation (20) - `stddev_20`

Mathematical definition: population standard deviation of `closes[-period:]` (the same calculation Bollinger Bands uses internally, also exposed as its own indicator per docs/08 §5).

Inputs: `closes`

Parameters: `period` = 20

Output fields: `value` = latest standard deviation.

Warm-up requirement: 20 candles.

Numerical precision: `float`; population standard deviation.

External reference/source: standard statistical definition.

---

# 5. Volume

## VWAP (Volume-Weighted Average Price) - `vwap`

Mathematical definition

```
typical_price[i] = (high[i] + low[i] + close[i]) / 3
VWAP = sum(typical_price[i] * volume[i] for all i) / sum(volume[i] for all i)
```

**Simplification note**: computed over the *entire* provided candle window, not a proper intraday session that resets daily - Phase 3A has no session-boundary concept yet (see `app/indicators/volume.py::vwap` docstring, BACKLOG.md §11). Revisit if session-based VWAP is needed.

Inputs: `highs`, `lows`, `closes`, `volumes`

Parameters: none (whole-window calculation)

Output fields: `value` = VWAP over the provided window.

Warm-up requirement: 1 candle with a non-null volume (returns `None` only if total volume is zero).

Numerical precision: `float`.

External reference/source: standard market-microstructure definition, widely used since the 1980s.

---

## OBV (On-Balance Volume) - `obv`

Mathematical definition

```
OBV[0] = 0
OBV[i] = OBV[i-1] + volume[i]   if close[i] > close[i-1]
OBV[i] = OBV[i-1] - volume[i]   if close[i] < close[i-1]
OBV[i] = OBV[i-1]               if close[i] == close[i-1]
```

Inputs: `closes`, `volumes`

Parameters: none

Output fields: `value` = the running OBV total over the provided window.

Warm-up requirement: 2 candles.

Numerical precision: `float`. **Note**: OBV is a *cumulative running total relative to the start of the provided window*, not an absolute, comparable-across-runs quantity - its magnitude depends on how much history `IndicatorService`'s lookback window includes (see BACKLOG.md §11's note on lookback window).

External reference/source: Joseph Granville, *Granville's New Key to Stock Market Profits* (1963).

---

## Volume SMA (20) - `volume_sma_20`

Mathematical definition: simple moving average of `volumes[-period:]` (null volumes excluded before averaging).

Inputs: `volumes`

Parameters: `period` = 20

Output fields: `value` = latest volume SMA.

Warm-up requirement: 20 candles with non-null volume.

Numerical precision: `float`.

External reference/source: standard moving-average definition applied to volume.

---

## Relative Volume (20) - `relative_volume_20`

Mathematical definition

```
average = SMA(volumes[:-1], period)   # average of the `period` bars preceding the current one
RelativeVolume = volumes[-1] / average
```

Inputs: `volumes`

Parameters: `period` = 20

Output fields: `value` = ratio of current volume to the trailing average (1.0 = average, >1.0 = above average).

Warm-up requirement: `period + 1` = 21 candles.

Numerical precision: `float`.

External reference/source: standard "relative volume" concept, widely used in intraday trading platforms.

---

# 6. Trend Strength

## ADX / DI+ / DI- (14) - `adx_14`

Mathematical definition (Wilder's original formulation)

```
up_move[i]   = high[i] - high[i-1]
down_move[i] = low[i-1] - low[i]
+DM[i] = up_move[i]   if up_move[i] > down_move[i] and up_move[i] > 0    else 0
-DM[i] = down_move[i] if down_move[i] > up_move[i] and down_move[i] > 0 else 0
TR[i]  = max(high[i]-low[i], |high[i]-close[i-1]|, |low[i]-close[i-1]|)

smoothed_TR, smoothed_+DM, smoothed_-DM = Wilder-smoothed series of TR, +DM, -DM (period)

+DI[i] = 100 * smoothed_+DM[i] / smoothed_TR[i]
-DI[i] = 100 * smoothed_-DM[i] / smoothed_TR[i]
DX[i]  = 100 * |+DI[i] - -DI[i]| / (+DI[i] + -DI[i])

ADX = Wilder-smoothed series of DX (period), latest value
```

Inputs: `highs`, `lows`, `closes`

Parameters: `period` = 14

Output fields: `value` = latest ADX (range 0-100, trend *strength* regardless of direction). `context.di_plus`, `context.di_minus` (directional indicators - compare them to infer direction).

Warm-up requirement: `2 * period` = 28 candles (`period + 1` to seed TR/DM smoothing, then another `period` DX values to seed the ADX smoothing itself - see `app/indicators/trend_strength.py::adx`).

Numerical precision: `float`; two nested Wilder-smoothing passes (DM/TR, then DX) - the most numerically involved calculation in this reference, but each pass individually is the same stable recurrence used by RSI/ATR.

External reference/source: J. Welles Wilder Jr., *New Concepts in Technical Trading Systems* (1978).

---

# 7. Summary Table

| Indicator | Registered name(s) | Params | Warm-up (candles) |
|---|---|---|---|
| EMA | `ema_20`, `ema_50`, `ema_100`, `ema_200` | period | = period |
| SMA | `sma_200` | period=200 | 200 |
| RSI | `rsi_14` | period=14 | 28 |
| MACD | `macd` | 12/26/9 | 34 |
| Stochastic RSI | `stoch_rsi_14` | period=14 | 28 |
| CCI | `cci_20` | period=20 | 20 |
| Momentum | `momentum_10` | period=10 | 11 |
| ATR | `atr_14` | period=14 | 15 |
| Bollinger Bands | `bollinger_bands_20` | 20/2.0 | 20 |
| Standard Deviation | `stddev_20` | period=20 | 20 |
| VWAP | `vwap` | none | 1 |
| OBV | `obv` | none | 2 |
| Volume SMA | `volume_sma_20` | period=20 | 20 |
| Relative Volume | `relative_volume_20` | period=20 | 21 |
| ADX / DI+ / DI- | `adx_14` | period=14 | 28 |

`IndicatorService._DEFAULT_LOOKBACK` (500 candles) comfortably covers every warm-up requirement above - see BACKLOG.md §11 if an indicator with a longer lookback need is ever added.
