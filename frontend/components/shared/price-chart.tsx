"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  HistogramSeries,
  LineSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type SeriesMarker,
  type SeriesMarkerShape,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { useTheme } from "next-themes";
import { useEffect, useMemo, useRef } from "react";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { computeMACD, computeRSI } from "@/lib/technical-indicators";
import type { LatestCandleResponse, Timeframe } from "@/services/types";

const TIMEFRAMES: Timeframe[] = ["m1", "m5", "m15", "m30", "h1", "h4", "d1", "w1", "mn"];

//: `lightweight-charts` formats time-axis labels in raw UTC by default,
//: not the viewer's local time - candle timestamps land here as UTC
//: epoch seconds and get relabeled straight through. Pinned to
//: Asia/Bangkok to match `lib/format.ts`'s UTC+7 convention elsewhere in
//: the app, rather than silently showing UTC.
const BANGKOK_TICK_FORMATTER = new Intl.DateTimeFormat("en-US", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "Asia/Bangkok",
});
const BANGKOK_CROSSHAIR_FORMATTER = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Asia/Bangkok",
});

export interface PriceLineOverlay {
  price: number;
  color: string;
  title: string;
}

/**
 * A price range (Order Block / Fair Value Gap) - rendered as a paired
 * top/bottom price line sharing a color and label prefix (ADR-107).
 * lightweight-charts has no built-in "shaded rectangle" primitive without
 * a custom plugin, so this reuses the same `createPriceLine` mechanism
 * `PriceLineOverlay` already uses rather than adding one.
 */
export interface ZoneOverlay {
  high: number;
  low: number;
  color: string;
  label: string;
}

/**
 * A point-in-time SMC event (BOS/CHoCH/Liquidity Sweep) - ADR-107.
 * Positioned relative to the bar (`aboveBar`/`belowBar`), not an exact
 * price - CHoCH events in particular have no price field to place an
 * exact marker at (only a confirmation time and trend change).
 */
export interface ChartMarkerOverlay {
  time: string | number;
  position: "aboveBar" | "belowBar";
  color: string;
  shape: SeriesMarkerShape;
  text: string;
}

/**
 * `lightweight-charts` candlestick chart + timeframe switcher + optional
 * overlays: price lines (Support/Resistance, Entry/SL/TP), zones (Order
 * Blocks/FVG), and time markers (BOS/CHoCH/Liquidity Sweeps) - docs/54
 * §3, ADR-105, ADR-107. No drawing tools, no live tick updates, no
 * fullscreen toggle this phase - see ADR-105 for the full reasoning;
 * ADR-107 only adds programmatic overlay *types*, not interactivity.
 */
export function PriceChart({
  candles,
  overlays = [],
  zones = [],
  markers = [],
  timeframe,
  onTimeframeChange,
  isLoading,
  showIndicators = false,
}: {
  candles: LatestCandleResponse[];
  overlays?: PriceLineOverlay[];
  zones?: ZoneOverlay[];
  markers?: ChartMarkerOverlay[];
  timeframe: Timeframe;
  onTimeframeChange: (timeframe: Timeframe) => void;
  isLoading?: boolean;
  //: Adds RSI(14)/MACD(12,26,9) sub-panes below the candlestick pane,
  //: computed client-side from `candles` (no backend indicator-series
  //: endpoint exists - `IndicatorResultResponse` only exposes the latest
  //: snapshot value, not a time series). Defaults off so the other three
  //: `PriceChart` call sites keep their current fixed height/layout.
  showIndicators?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const rsiSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const macdLineSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const macdSignalSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const macdHistSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const candlesRef = useRef<LatestCandleResponse[]>(candles);
  candlesRef.current = candles;
  const { resolvedTheme } = useTheme();

  const indicatorSeries = useMemo(() => {
    if (!showIndicators || candles.length === 0) return null;
    const times = candles.map((candle) => (new Date(candle.timestamp).getTime() / 1000) as UTCTimestamp);
    const closes = candles.map((candle) => Number(candle.close));
    const rsi = computeRSI(closes);
    const macd = computeMACD(closes);
    return {
      rsi: times.map((time, i) => ({ time, value: rsi[i] })).filter((point) => point.value !== null),
      macdLine: times.map((time, i) => ({ time, value: macd.macd[i] })).filter((point) => point.value !== null),
      signal: times.map((time, i) => ({ time, value: macd.signal[i] })).filter((point) => point.value !== null),
      histogram: times
        .map((time, i) => ({
          time,
          value: macd.histogram[i],
          color: (macd.histogram[i] ?? 0) >= 0 ? "#22C55E" : "#EF4444",
        }))
        .filter((point) => point.value !== null),
    } as {
      rsi: { time: UTCTimestamp; value: number }[];
      macdLine: { time: UTCTimestamp; value: number }[];
      signal: { time: UTCTimestamp; value: number }[];
      histogram: { time: UTCTimestamp; value: number; color: string }[];
    };
  }, [candles, showIndicators]);

  // Create the chart once per mount. `autoSize: true` internally wires a
  // ResizeObserver whose callback can still fire (and paint into an
  // already-disposed canvas, throwing "Object is disposed") after
  // `chart.remove()` if a resize is queued right as the component
  // unmounts (e.g. fast route navigation) - manually managing the
  // ResizeObserver and disconnecting it *before* `chart.remove()`
  // eliminates that race.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#9CA3AF" },
      grid: {
        vertLines: { color: "rgba(148, 163, 184, 0.1)" },
        horzLines: { color: "rgba(148, 163, 184, 0.1)" },
      },
      localization: {
        timeFormatter: (time: Time) => BANGKOK_CROSSHAIR_FORMATTER.format(new Date((time as number) * 1000)),
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: Time) => BANGKOK_TICK_FORMATTER.format(new Date((time as number) * 1000)),
      },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#22C55E",
      downColor: "#EF4444",
      borderVisible: false,
      wickUpColor: "#22C55E",
      wickDownColor: "#EF4444",
      // `createPriceLine` (Support/Resistance/Order Block overlays below)
      // counts toward the default autoscale range - an overlay far outside
      // the actual candle range (e.g. a stale SMC order block) squeezes
      // every real candle into a sliver at one edge. Scale to the candle
      // data only, same as TradingView's own charts do.
      autoscaleInfoProvider: () => {
        const values = candlesRef.current;
        if (values.length === 0) return null;
        let min = Number(values[0].low);
        let max = Number(values[0].high);
        for (const candle of values) {
          min = Math.min(min, Number(candle.low));
          max = Math.max(max, Number(candle.high));
        }
        return { priceRange: { minValue: min, maxValue: max } };
      },
      // TradingView's floating current-price tag on the right axis - this
      // is `lightweight-charts`' built-in last-value indicator, made
      // explicit (and thicker/solid) so it reads as the live price rather
      // than blending into the Support/Resistance/Order Block overlay
      // lines drawn on the same series below.
      priceLineVisible: true,
      priceLineWidth: 2,
      priceLineStyle: LineStyle.Solid,
      lastValueVisible: true,
    });

    chartRef.current = chart;
    seriesRef.current = series;
    markersPluginRef.current = createSeriesMarkers(series, []);

    if (showIndicators) {
      // Pane 0 is the candlestick pane created above; pane 1/2 are
      // created implicitly the first time a series targets that index
      // (lightweight-charts v5 multi-pane API).
      const rsiSeries = chart.addSeries(LineSeries, { color: "#A78BFA", lineWidth: 1, title: "RSI 14" }, 1);
      rsiSeries.createPriceLine({ price: 70, color: "rgba(148, 163, 184, 0.5)", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: "" });
      rsiSeries.createPriceLine({ price: 30, color: "rgba(148, 163, 184, 0.5)", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: "" });
      rsiSeriesRef.current = rsiSeries;

      const macdHistSeries = chart.addSeries(HistogramSeries, { title: "MACD Hist" }, 2);
      macdHistSeriesRef.current = macdHistSeries;
      const macdLineSeries = chart.addSeries(LineSeries, { color: "#3B82F6", lineWidth: 1, title: "MACD" }, 2);
      macdLineSeriesRef.current = macdLineSeries;
      const macdSignalSeries = chart.addSeries(LineSeries, { color: "#F59E0B", lineWidth: 1, title: "Signal" }, 2);
      macdSignalSeriesRef.current = macdSignalSeries;

      const panes = chart.panes();
      panes[0]?.setHeight(220);
      panes[1]?.setHeight(90);
      panes[2]?.setHeight(90);
    }

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      chart.resize(entry.contentRect.width, entry.contentRect.height);
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      markersPluginRef.current = null;
      rsiSeriesRef.current = null;
      macdLineSeriesRef.current = null;
      macdSignalSeriesRef.current = null;
      macdHistSeriesRef.current = null;
    };
    // `showIndicators` is treated as fixed per call site (mirrors this
    // effect's existing mount-once pattern) - toggling it at runtime
    // would require tearing down and recreating the chart, not supported.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Theme-sync the text color (docs/54 §3's "Theme Sync" requirement).
  useEffect(() => {
    if (!chartRef.current) return;
    chartRef.current.applyOptions({
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: resolvedTheme === "dark" ? "#9CA3AF" : "#64748B",
      },
    });
  }, [resolvedTheme]);

  // Push candle data whenever it changes.
  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return;
    seriesRef.current.setData(
      candles.map((candle) => ({
        time: (new Date(candle.timestamp).getTime() / 1000) as UTCTimestamp,
        open: Number(candle.open),
        high: Number(candle.high),
        low: Number(candle.low),
        close: Number(candle.close),
      })),
    );
    chartRef.current.timeScale().fitContent();
  }, [candles]);

  // Push RSI/MACD data into the indicator panes whenever it changes.
  useEffect(() => {
    if (!indicatorSeries) return;
    rsiSeriesRef.current?.setData(indicatorSeries.rsi);
    macdHistSeriesRef.current?.setData(indicatorSeries.histogram);
    macdLineSeriesRef.current?.setData(indicatorSeries.macdLine);
    macdSignalSeriesRef.current?.setData(indicatorSeries.signal);
  }, [indicatorSeries]);

  // Redraw overlay price lines whenever they change.
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;

    const lines = overlays.map((overlay) =>
      series.createPriceLine({
        price: overlay.price,
        color: overlay.color,
        lineWidth: 1,
        lineStyle: 2, // dashed
        axisLabelVisible: true,
        title: overlay.title,
      }),
    );

    return () => {
      // `series` may already be disposed (`chart.remove()`) by the time
      // this cleanup runs, if the unmount races with an overlay-props
      // change - removePriceLine on a disposed series throws, same
      // class of issue as the ResizeObserver race above.
      if (seriesRef.current !== series) return;
      for (const line of lines) series.removePriceLine(line);
    };
  }, [overlays]);

  // Redraw zone overlays (Order Blocks/FVG) as paired top/bottom price
  // lines whenever they change (ADR-107).
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;

    const lines = zones.flatMap((zone) => [
      series.createPriceLine({
        price: zone.high,
        color: zone.color,
        lineWidth: 1,
        lineStyle: 3, // dotted
        axisLabelVisible: true,
        title: `${zone.label} top`,
      }),
      series.createPriceLine({
        price: zone.low,
        color: zone.color,
        lineWidth: 1,
        lineStyle: 3,
        axisLabelVisible: true,
        title: `${zone.label} bottom`,
      }),
    ]);

    return () => {
      if (seriesRef.current !== series) return;
      for (const line of lines) series.removePriceLine(line);
    };
  }, [zones]);

  // Redraw time markers (BOS/CHoCH/Liquidity Sweeps) whenever they change
  // (ADR-107) via the native `createSeriesMarkers` plugin.
  useEffect(() => {
    const plugin = markersPluginRef.current;
    if (!plugin) return;

    const seriesMarkers: SeriesMarker<Time>[] = markers
      .map((marker) => ({
        time: (typeof marker.time === "number" ? marker.time : new Date(marker.time).getTime() / 1000) as UTCTimestamp,
        position: marker.position,
        shape: marker.shape,
        color: marker.color,
        text: marker.text,
      }))
      .sort((a, b) => (a.time as number) - (b.time as number));

    plugin.setMarkers(seriesMarkers);

    return () => {
      if (markersPluginRef.current !== plugin) return;
      plugin.setMarkers([]);
    };
  }, [markers]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">Price Chart</p>
        <div className="flex items-center gap-2">
          {isLoading ? <p className="text-xs text-muted-foreground">Loading candles…</p> : null}
          <Select value={timeframe} onValueChange={(value) => onTimeframeChange(value as Timeframe)}>
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIMEFRAMES.map((tf) => (
                <SelectItem key={tf} value={tf}>
                  {tf.toUpperCase()}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <div
        className={`relative w-full rounded-md border border-border bg-muted/5 p-2 ${showIndicators ? "h-[420px]" : "h-[360px]"}`}
      >
        {isLoading && candles.length === 0 ? <Skeleton className="absolute inset-0" /> : null}
        <div ref={containerRef} className="h-full w-full" />
      </div>
    </div>
  );
}
