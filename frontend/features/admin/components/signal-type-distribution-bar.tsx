import { formatEnumLabel } from "@/lib/format";

/**
 * A plain CSS proportion bar for `GET /admin/analytics`'s
 * `signal_type_distribution` (docs/58 §3.2, ADR-131) - deliberately not a
 * chart library. The full response is four scalars and a ~2-key
 * dictionary; docs/58 §3.3's "first chart dependency" premise assumed
 * docs/25 §15's much richer analytics set, which ADR-130 deferred for
 * lack of view-tracking/latency infrastructure. `bull`/`bear` reuse the
 * same buy/sell color tokens `Delta`/price displays already use
 * elsewhere in the app.
 */
const SEGMENT_COLOR: Record<string, string> = {
  buy: "bg-bull",
  sell: "bg-bear",
};

export function SignalTypeDistributionBar({
  distribution,
}: {
  distribution: Record<string, number>;
}) {
  const entries = Object.entries(distribution);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);

  if (total === 0) {
    return <p className="text-[11px] text-muted-foreground">No signals yet.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-surface-2">
        {entries.map(([type, count]) => (
          <div
            key={type}
            className={SEGMENT_COLOR[type] ?? "bg-muted-foreground/40"}
            style={{ width: `${(count / total) * 100}%` }}
            title={`${formatEnumLabel(type)}: ${count}`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1">
        {entries.map(([type, count]) => (
          <div key={type} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className={`size-2 rounded-full ${SEGMENT_COLOR[type] ?? "bg-muted-foreground/40"}`} />
            {formatEnumLabel(type)}: <span className="font-medium tabular-nums text-foreground">{count}</span>
            <span>({((count / total) * 100).toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}
