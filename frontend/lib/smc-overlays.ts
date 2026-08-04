import type { ChartMarkerOverlay, PriceLineOverlay, ZoneOverlay } from "@/components/shared/price-chart";
import type { SMCAnalysisResponse } from "@/services/types";

/**
 * Maps `useSMCAnalysis()` data to `PriceChart` zone/marker overlays
 * (ADR-107). Shared by every page that draws SMC overlays (Markets
 * detail, Signal detail, AI Analysis detail) so the mapping - and the
 * "top N" capping convention already established for Order Blocks on
 * the Markets detail page - is defined once.
 */
export type SmcOverlayKind = "order_blocks" | "fair_value_gaps" | "bos" | "choch" | "liquidity";

export const SMC_OVERLAY_LABELS: Record<SmcOverlayKind, string> = {
  order_blocks: "Order Blocks",
  fair_value_gaps: "Fair Value Gaps",
  bos: "BOS",
  choch: "CHoCH",
  liquidity: "Liquidity",
};

export const DEFAULT_SMC_OVERLAYS: SmcOverlayKind[] = ["order_blocks", "bos"];

const TOP_N = 3;

export function buildSmcOverlays(
  smc: SMCAnalysisResponse | undefined,
  enabled: ReadonlySet<SmcOverlayKind>,
): { zones: ZoneOverlay[]; markers: ChartMarkerOverlay[]; lines: PriceLineOverlay[] } {
  const zones: ZoneOverlay[] = [];
  const markers: ChartMarkerOverlay[] = [];
  const lines: PriceLineOverlay[] = [];
  if (!smc) return { zones, markers, lines };

  if (enabled.has("order_blocks")) {
    for (const block of [...smc.order_blocks].sort((a, b) => b.strength_score - a.strength_score).slice(0, TOP_N)) {
      zones.push({
        high: Number(block.zone_high),
        low: Number(block.zone_low),
        color: block.direction === "bullish" ? "#22C55E" : "#EF4444",
        label: `OB ${block.direction}`,
      });
    }
  }

  if (enabled.has("fair_value_gaps")) {
    for (const gap of smc.fair_value_gaps.slice(0, TOP_N)) {
      zones.push({
        high: Number(gap.gap_high),
        low: Number(gap.gap_low),
        color: gap.direction === "bullish" ? "#3B82F6" : "#F59E0B",
        label: `FVG ${gap.direction}`,
      });
    }
  }

  if (enabled.has("bos")) {
    for (const event of smc.bos.slice(0, TOP_N)) {
      markers.push({
        time: event.break_time,
        position: event.direction === "bullish" ? "belowBar" : "aboveBar",
        color: event.direction === "bullish" ? "#22C55E" : "#EF4444",
        shape: event.direction === "bullish" ? "arrowUp" : "arrowDown",
        text: "BOS",
      });
    }
  }

  if (enabled.has("choch")) {
    for (const event of smc.choch.slice(0, TOP_N)) {
      const bullish = event.new_trend === "bullish";
      markers.push({
        time: event.confirmation_time,
        position: bullish ? "belowBar" : "aboveBar",
        color: "#F59E0B",
        shape: "circle",
        text: "CHoCH",
      });
    }
  }

  if (enabled.has("liquidity")) {
    for (const zone of [...smc.liquidity_zones].sort((a, b) => b.touch_count - a.touch_count).slice(0, TOP_N)) {
      lines.push({
        price: Number(zone.level),
        color: zone.side === "buy_side" ? "#22C55E" : "#EF4444",
        title: `Liquidity ${zone.side === "buy_side" ? "buy" : "sell"}`,
      });
    }
  }

  return { zones, markers, lines };
}
