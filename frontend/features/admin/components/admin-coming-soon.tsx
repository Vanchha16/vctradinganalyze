import type { LucideIcon } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { Panel } from "@/components/shared/premium";

/**
 * Phase 8C only built `/admin/users*` - `/admin/logs`, `/admin/system`,
 * `/admin/analytics` (Signal Statistics), and true API-usage telemetry
 * were never built (docs/59 §10.1/§12, same category of gap as the
 * Watchlists placeholder, ADR-103: no fake data, no client-side-only fake
 * persistence). Every page below reuses this rather than inventing five
 * near-identical "coming soon" blocks.
 */
export function AdminComingSoon({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <Panel>
      <EmptyState icon={Icon} title={title} description={description} />
    </Panel>
  );
}
