import type { ChartMarkerOverlay } from "@/components/shared/price-chart";
import type { LatestCandleResponse, SignalResponse } from "@/services/types";

/**
 * Chart markers for a signal's own lifecycle events - created, entry
 * confirmed, closed - so the candle where entry was actually confirmed
 * is visible on the chart rather than only as a timestamp in the
 * timeline panel.
 *
 * Distinct from `lib/smc-overlays.ts`, which marks *market structure*
 * (BOS/CHoCH/Liquidity). These mark what happened to this one signal.
 *
 * Worth stating plainly: these timestamps are only trustworthy because
 * of ADR-141. Before that fix `triggered_at`/`closed_at` recorded
 * `datetime.now()` at the moment the monitor happened to notice -
 * routinely hours after the fact - so a marker drawn from them would
 * have pointed at the wrong candle. They now record the timestamp of
 * the candle that actually touched the level.
 */

/** Snap an event time to the bar that contains it.
 *
 * Necessary because the event timestamp comes from an **M1** candle
 * (`signal_monitoring_tasks._PRICE_TIMEFRAME`) while the chart may be
 * showing M5/H1/D1. `setMarkers` positions by exact bar time, so an
 * unsnapped M1 timestamp would not line up with any bar on those
 * timeframes. Returns the last bar opening at or before the event -
 * i.e. the bar the event happened *inside*.
 */
function snapToBar(eventIso: string, barTimes: number[], barInterval: number): number | null {
  const eventSeconds = new Date(eventIso).getTime() / 1000;
  if (Number.isNaN(eventSeconds)) return null;

  const lastBar = barTimes[barTimes.length - 1];
  // An event *after* the newest bar has no bar to point at. Snapping it
  // to the last bar anyway would silently claim the entry was confirmed
  // at a candle it has nothing to do with - which is exactly the class of
  // quiet inaccuracy ADR-141 was about. One interval of slack covers the
  // still-forming final bar; beyond that, draw nothing.
  if (eventSeconds > lastBar + barInterval) return null;

  let match: number | null = null;
  for (const barTime of barTimes) {
    if (barTime <= eventSeconds) match = barTime;
    else break; // barTimes is ascending; nothing later can match
  }
  // `null` also means the event predates the loaded window - the chart
  // does not reach back that far, so again there is no bar to point at.
  return match;
}

/** Smallest positive gap between bars - the timeframe's period, derived
 *  from the data rather than passed in, so it stays correct when the
 *  viewer switches the chart's timeframe independently of the signal's. */
function inferBarInterval(barTimes: number[]): number {
  let smallest = Number.POSITIVE_INFINITY;
  for (let i = 1; i < barTimes.length; i += 1) {
    const gap = barTimes[i] - barTimes[i - 1];
    if (gap > 0 && gap < smallest) smallest = gap;
  }
  return Number.isFinite(smallest) ? smallest : 0;
}

function outcomeLabel(signal: SignalResponse): { text: string; color: string } {
  if (signal.status === "successful") return { text: "Take Profit hit", color: "#22C55E" };
  if (signal.status === "stopped_out") return { text: "Stop Loss hit", color: "#EF4444" };
  return { text: "Closed", color: "#94A3B8" };
}

export function buildSignalLifecycleMarkers(
  signal: SignalResponse,
  candles: LatestCandleResponse[],
): ChartMarkerOverlay[] {
  if (candles.length === 0) return [];

  const barTimes = candles
    .map((candle) => new Date(candle.timestamp).getTime() / 1000)
    .sort((a, b) => a - b);
  const barInterval = inferBarInterval(barTimes);

  const markers: ChartMarkerOverlay[] = [];

  // Created: where the signal was issued. Deliberately included even
  // though only "triggered" was asked for - the gap between this marker
  // and the entry-confirmed one is exactly the entry-placement problem
  // ADR-145 fixed, and seeing it on the chart is the quickest way to
  // tell a signal that filled immediately from one that waited.
  const createdAt = snapToBar(signal.created_at, barTimes, barInterval);
  if (createdAt !== null) {
    markers.push({
      time: createdAt,
      position: "aboveBar",
      color: "#94A3B8",
      shape: "circle",
      text: "Signal created",
    });
  }

  // Entry confirmed - the candle whose range actually covered the entry
  // price (ADR-137's touch rule). This is the one that was asked for.
  if (signal.triggered_at) {
    const triggeredAt = snapToBar(signal.triggered_at, barTimes, barInterval);
    if (triggeredAt !== null) {
      markers.push({
        time: triggeredAt,
        position: "aboveBar",
        // Points down *at* the candle, rather than sitting beside it.
        shape: "arrowDown",
        // Matches the blue "Entry" price line already on the chart, so
        // the marker and the level it refers to read as one thing.
        color: "#3B82F6",
        text: "Entry confirmed",
      });
    }
  }

  if (signal.closed_at) {
    const closedAt = snapToBar(signal.closed_at, barTimes, barInterval);
    if (closedAt !== null) {
      const outcome = outcomeLabel(signal);
      markers.push({
        // Below the bar so it never collides with the entry marker when
        // a signal fills and resolves on the same candle (ADR-137 §3.3's
        // gap/spike case, which is exactly when both land together).
        time: closedAt,
        position: "belowBar",
        shape: "arrowUp",
        color: outcome.color,
        text: outcome.text,
      });
    }
  }

  return markers;
}
