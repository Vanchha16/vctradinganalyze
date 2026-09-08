"use client";

/**
 * Proportion of 2xx/3xx/4xx/5xx responses as a plain-CSS bar (ADR-144).
 *
 * No chart library, per ADR-131's precedent - a four-segment proportion
 * bar does not justify a dependency, and this project has never shipped
 * one. (This deliberately re-treads the ground of the
 * `SignalTypeDistributionBar` deleted with Signal Statistics in ADR-142;
 * that component was not recoverable as a shared abstraction because it
 * was hardcoded to BUY/SELL, but its reasoning applies unchanged.)
 */
export function StatusClassBar({
  counts,
}: {
  counts: { label: string; value: number; className: string }[];
}) {
  const total = counts.reduce((sum, segment) => sum + segment.value, 0);

  if (total === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No responses recorded yet since the API last restarted.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-muted">
        {counts.map((segment) =>
          segment.value > 0 ? (
            <div
              key={segment.label}
              className={segment.className}
              style={{ width: `${(segment.value / total) * 100}%` }}
              title={`${segment.label}: ${segment.value}`}
            />
          ) : null,
        )}
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1.5">
        {counts.map((segment) => (
          <div key={segment.label} className="flex items-center gap-2">
            <span className={`size-2 rounded-full ${segment.className}`} />
            <span className="text-xs text-muted-foreground">
              {segment.label}{" "}
              <span className="font-medium text-foreground">{segment.value.toLocaleString()}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
