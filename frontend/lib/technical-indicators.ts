//: Pure client-side RSI/MACD computation over an already-fetched close
//: array - lets `PriceChart` render indicator sub-panes (RSI 14, MACD
//: 12/26/9) without a new backend endpoint. Values line up index-for-index
//: with the input `closes` array; `null` marks the warm-up period before
//: enough history exists.

export function computeRSI(closes: number[], period = 14): (number | null)[] {
  const rsi: (number | null)[] = new Array(closes.length).fill(null);
  if (closes.length <= period) return rsi;

  let gainSum = 0;
  let lossSum = 0;
  for (let i = 1; i <= period; i++) {
    const change = closes[i] - closes[i - 1];
    if (change >= 0) gainSum += change;
    else lossSum -= change;
  }
  let avgGain = gainSum / period;
  let avgLoss = lossSum / period;
  rsi[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);

  for (let i = period + 1; i < closes.length; i++) {
    const change = closes[i] - closes[i - 1];
    const gain = change > 0 ? change : 0;
    const loss = change < 0 ? -change : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    rsi[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return rsi;
}

function computeEMA(values: number[], period: number): (number | null)[] {
  const ema: (number | null)[] = new Array(values.length).fill(null);
  const k = 2 / (period + 1);
  let prev: number | null = null;

  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) continue;
    if (prev === null) {
      const seed = values.slice(i - period + 1, i + 1);
      prev = seed.reduce((a, b) => a + b, 0) / period;
    } else {
      prev = values[i] * k + prev * (1 - k);
    }
    ema[i] = prev;
  }
  return ema;
}

export interface MACDResult {
  macd: (number | null)[];
  signal: (number | null)[];
  histogram: (number | null)[];
}

export function computeMACD(closes: number[], fast = 12, slow = 26, signalPeriod = 9): MACDResult {
  const emaFast = computeEMA(closes, fast);
  const emaSlow = computeEMA(closes, slow);
  const macdLine = closes.map((_, i) => {
    const f = emaFast[i];
    const s = emaSlow[i];
    return f !== null && s !== null ? f - s : null;
  });

  // The signal line is an EMA of the MACD line itself, but EMA warm-up
  // needs a contiguous array - compact out the leading nulls, run EMA,
  // then scatter the results back onto the full-length array.
  const compactMacd = macdLine.filter((v): v is number => v !== null);
  const compactSignal = computeEMA(compactMacd, signalPeriod);
  const signal: (number | null)[] = new Array(closes.length).fill(null);
  let compactIndex = 0;
  for (let i = 0; i < macdLine.length; i++) {
    if (macdLine[i] === null) continue;
    signal[i] = compactSignal[compactIndex] ?? null;
    compactIndex++;
  }

  const histogram = macdLine.map((m, i) => {
    const s = signal[i];
    return m !== null && s !== null ? m - s : null;
  });

  return { macd: macdLine, signal, histogram };
}
