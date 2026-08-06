import { ApiError } from "@/services/api-client";
import { Button } from "@/components/ui/button";

/**
 * `notFoundHint` is caller-supplied, not hardcoded - this card is shared
 * across every list/detail page in the app, and a single hardcoded
 * "no candle data" hint (this component's original shape) was wrong on
 * every page except the one it was written for, and silently wrong once
 * a second page adopted `ErrorCard` (surfaced on the Watchlist detail
 * page's 404, BACKLOG.md §26). Only shown for a `resource_not_found`
 * error and only when a caller actually supplies one - no hint at all
 * beats a wrong one.
 */
export function ErrorCard({
  error,
  onRetry,
  notFoundHint,
}: {
  error: unknown;
  onRetry: () => void;
  notFoundHint?: string;
}) {
  const message = error instanceof ApiError ? error.message : "Something went wrong.";
  const hint =
    error instanceof ApiError && error.errorCode === "resource_not_found" ? notFoundHint : null;

  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      <div className="grid size-12 place-items-center rounded-xl border border-bear/30 bg-bear/10 text-bear">
        <svg viewBox="0 0 24 24" className="size-5 fill-none stroke-current stroke-[1.8]">
          <path d="M12 8v5M12 17h.01M10.3 3.3 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.3a2 2 0 0 0-3.4 0Z" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-semibold text-bear">{message}</p>
        {hint ? <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-muted-foreground">{hint}</p> : null}
      </div>
      <Button size="sm" variant="outline" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}
