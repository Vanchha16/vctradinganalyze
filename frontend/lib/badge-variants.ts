import type { BadgeProps } from "@/components/ui/badge";

type Variant = NonNullable<BadgeProps["variant"]>;

/**
 * Centralizes every enum-to-Badge-variant mapping used across pages -
 * previously inlined ad hoc per page (e.g. the Phase 6 dev dashboard's
 * `TREND_VARIANT`/`STRUCTURE_VARIANT`/`REGIME_VARIANT`). Every page
 * showing one of these enums reuses the same mapping instead of
 * redefining it (docs/54 §4).
 */

export function recommendationVariant(value: string): Variant {
  if (value === "buy") return "success";
  if (value === "sell") return "destructive";
  return "secondary"; // wait
}

export function signalStatusVariant(value: string): Variant {
  if (value === "active") return "success";
  if (value === "stopped_out" || value === "cancelled") return "destructive";
  if (value === "successful") return "success";
  if (value === "expired" || value === "closed") return "secondary";
  return "outline"; // draft, triggered
}

export function confidenceLevelVariant(value: string): Variant {
  if (value === "very_high" || value === "high") return "success";
  if (value === "moderate") return "warning";
  return "destructive"; // low, very_low
}

export function riskLevelVariant(value: string): Variant {
  if (value === "low") return "success";
  if (value === "medium") return "warning";
  return "destructive"; // high
}

export function newsSentimentVariant(value: string): Variant {
  if (value === "very_bullish" || value === "bullish") return "success";
  if (value === "very_bearish" || value === "bearish") return "destructive";
  return "secondary"; // neutral
}

export function importanceVariant(value: string): Variant {
  if (value === "critical") return "destructive";
  if (value === "high") return "warning";
  if (value === "medium") return "secondary";
  return "outline"; // low, ignore
}

export function trendDirectionVariant(value: string): Variant {
  if (value === "bullish") return "success";
  if (value === "bearish") return "destructive";
  return "secondary"; // sideways
}

export function marketStructureVariant(value: string): Variant {
  if (value === "bullish") return "success";
  if (value === "bearish") return "destructive";
  return "secondary"; // range, transition
}

export function marketRegimeVariant(value: string): Variant {
  if (value === "trending_bullish" || value === "accumulation") return "success";
  if (value === "trending_bearish" || value === "distribution") return "destructive";
  if (value === "breakout" || value === "pullback" || value === "reversal" || value === "high_volatility") {
    return "warning";
  }
  return "secondary"; // ranging, low_volatility, uncertain
}

export function assetActiveVariant(isActive: boolean): Variant {
  return isActive ? "success" : "secondary";
}
