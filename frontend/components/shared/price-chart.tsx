"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type SeriesMarker,
  type SeriesMarkerShape,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import type { LatestCandleResponse, Timeframe } from "@/services/types";

const TIMEFRAMES: Timeframe[] = ["m1", "m5", "m15", "m30", "h1", "h4", "d1", "w1", "mn"];

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
}: {
  candles: LatestCandleResponse[];
  overlays?: PriceLineOverlay[];
  zones?: ZoneOverlay[];
  markers?: ChartMarkerOverlay[];
  timeframe: Timeframe;
  onTimeframeChange: (timeframe: Timeframe) => void;
  isLoading?: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  const { resolvedTheme } = useTheme();

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
      timeScale: { timeVisible: true, secondsVisible: false },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#22C55E",
      downColor: "#EF4444",
      borderVisible: false,
      wickUpColor: "#22C55E",
      wickDownColor: "#EF4444",
    });

    chartRef.current = chart;
    seriesRef.current = series;
    markersPluginRef.current = createSeriesMarkers(series, []);

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
    };
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
      <div className="relative h-[360px] w-full rounded-md border border-border bg-muted/5 p-2">
        {isLoading && candles.length === 0 ? <Skeleton className="absolute inset-0" /> : null}
        <div ref={containerRef} className="h-full w-full" />
      </div>
    </div>
  );
}
