import { Skeleton } from "@/components/ui/skeleton";

/**
 * Shaped skeleton presets built on the existing `Skeleton` primitive -
 * every list/card loading state across the app previously hand-picked a
 * single flat-block height (`h-16`/`h-32`/`h-48`) per call site. These
 * mimic the actual content shape (badge chip + text lines, or a compact
 * row) so the loading state reads as "this content is arriving," not an
 * unrelated gray rectangle. Phase 7D polish only - no new data/props.
 */

/** A compact row: leading badge-shaped chip + two text lines - AI Analysis history, AI Chat conversation list, News list items. */
export function ListItemSkeleton() {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-border px-4 py-3">
      <div className="flex flex-1 flex-col gap-2">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <Skeleton className="h-5 w-16 rounded-full" />
    </div>
  );
}

/** A stat-grid card: badge row + 4-column stat grid - Signal cards. */
export function CardSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border p-4">
      <div className="flex items-center gap-2">
        <Skeleton className="h-5 w-20 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <div className="grid grid-cols-2 gap-3 border-t border-border pt-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="flex flex-col gap-1.5">
            <Skeleton className="h-3 w-10" />
            <Skeleton className="h-4 w-14" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** A dashboard widget body: a few icon+text rows - shared by all `WidgetCard` consumers instead of one flat `h-32` block each. */
export function WidgetSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 3 }).map((_, index) => (
        <div key={index} className="flex items-center justify-between gap-2 px-2 py-1.5">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-14 rounded-full" />
        </div>
      ))}
    </div>
  );
}

/** A chart area - already used by `price-chart-lazy.tsx`, extracted here for reuse. */
export function ChartSkeleton() {
  return <Skeleton className="h-[360px] w-full" />;
}
