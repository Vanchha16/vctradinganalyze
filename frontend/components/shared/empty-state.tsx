import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

/**
 * Generic empty-state (docs/05_FRONTEND_GUIDELINES.md §15) - every future
 * "no signals"/"no watchlist"/"no news" page reuses this instead of a
 * one-off per page.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      <div className="grid size-12 place-items-center rounded-xl border border-border bg-surface text-muted-foreground">
        <Icon className="size-5" aria-hidden />
      </div>
      <div>
        <p className="text-sm font-semibold">{title}</p>
        {description ? <p className="mx-auto mt-1 max-w-xs text-xs leading-relaxed text-muted-foreground">{description}</p> : null}
      </div>
      {action ? <div className="pt-1">{action}</div> : null}
    </div>
  );
}
