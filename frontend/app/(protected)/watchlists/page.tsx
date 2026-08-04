import { Star } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { PageContainer } from "@/features/dashboard/components/page-container";

/**
 * Coming-soon placeholder (ADR-103) - no backend exists for Watchlists
 * (no model, table, or route). No fake data, no client-side-only fake
 * persistence.
 */
export default function WatchlistsPage() {
  return (
    <div>
      <PageHeader title="Watchlists" description="Track your favorite assets in one place." />
      <PageContainer>
        <EmptyState
          icon={Star}
          title="Watchlists coming soon"
          description="This feature is on the roadmap and will let you group and monitor assets you care about most."
        />
      </PageContainer>
    </div>
  );
}
