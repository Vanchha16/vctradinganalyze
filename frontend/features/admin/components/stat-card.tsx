import type { LucideIcon } from "lucide-react";

import { Panel } from "@/components/shared/premium";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Extracted from `admin/page.tsx` (Phase 8D) so `admin/system-health`
 * (Phase 7D-D) can reuse the identical stat-tile shape instead of a
 * second copy - both pages follow the same "no fabricated numbers, every
 * stat is a real, currently-derivable count" principle.
 */
export function StatCard({
  label,
  value,
  icon: Icon,
  isLoading,
}: {
  label: string;
  value: number | undefined;
  icon: LucideIcon;
  isLoading: boolean;
}) {
  return (
    <Panel className="p-4">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
        <Icon className="size-4 text-muted-foreground" />
      </div>
      {isLoading ? (
        <Skeleton className="mt-2 h-8 w-16" />
      ) : (
        <p className="mt-1 text-2xl font-semibold tabular-nums">{value ?? "—"}</p>
      )}
    </Panel>
  );
}
