import { formatEnumLabel, formatPrice } from "@/lib/format";
import type { EaEventResponse, EaEventType } from "@/services/types";

export const EA_EVENT_LABELS: Record<EaEventType, string> = {
  dry_run_checked: "Dry-run check",
  order_placed: "Order placed",
  order_skipped: "Skipped",
  order_rejected: "Rejected",
  order_cancelled: "Cancelled",
  position_opened: "Filled",
  position_closed: "Closed",
};

const CLOSE_REASONS: Record<string, string> = {
  tp: "take profit",
  sl: "stop loss",
  stop_out: "stop out",
  manual: "manual close",
  expert: "EA",
  other: "broker",
};

function orderText(event: EaEventResponse): string {
  const parts: string[] = [];
  if (event.order_type) parts.push(formatEnumLabel(event.order_type).toUpperCase());
  if (event.volume !== null) parts.push(`${event.volume} lot`);
  if (event.price !== null) parts.push(`@ ${formatPrice(event.price)}`);
  return parts.join(" ");
}

function suffix(text: string | null | undefined): string {
  return text ? ` · ${text}` : "";
}

/** One line saying what happened, in the EA's own terms. */
export function describeEaEvent(event: EaEventResponse): string {
  switch (event.event_type) {
    case "dry_run_checked":
      return `Would place ${orderText(event)}${suffix(event.message)}`;
    case "order_placed":
      return `Placed ${orderText(event)}${event.order_ticket ? ` · #${event.order_ticket}` : ""}`;
    case "order_skipped":
      return event.message ?? "Not traded";
    case "order_rejected":
      return `Broker refused${event.retcode !== null ? ` (${event.retcode})` : ""}${suffix(event.message)}`;
    case "order_cancelled":
      return `Cancelled${event.order_ticket ? ` #${event.order_ticket}` : ""}${suffix(event.message)}`;
    case "position_opened":
      return `Filled ${orderText(event)}`;
    case "position_closed": {
      const reason = event.close_reason ? ` by ${CLOSE_REASONS[event.close_reason] ?? event.close_reason}` : "";
      const price = event.price !== null ? ` @ ${formatPrice(event.price)}` : "";
      return `Closed${reason}${price}`;
    }
    default:
      return formatEnumLabel(event.event_type);
  }
}

/** Signed profit with its currency, or null when the event has none. */
export function formatEaProfit(event: EaEventResponse): string | null {
  if (event.profit === null) return null;
  const sign = event.profit > 0 ? "+" : "";
  return `${sign}${event.profit.toFixed(2)} ${event.currency ?? ""}`.trim();
}

export function profitClass(event: EaEventResponse): string {
  if (event.profit === null || event.profit === 0) return "text-muted-foreground";
  return event.profit > 0 ? "text-success" : "text-destructive";
}
