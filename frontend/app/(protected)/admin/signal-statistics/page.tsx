import { TrendingUp } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { AdminComingSoon } from "@/features/admin/components/admin-coming-soon";
import { PageContainer } from "@/features/dashboard/components/page-container";

/** `GET /admin/signals`/`GET /admin/analytics` (per-user signal
 * distribution, recommendation breakdown across all users) were not built
 * in Phase 8C. The existing `GET /signals` is scoped to the caller's own
 * signals, not an admin-wide aggregate. */
export default function AdminSignalStatisticsPage() {
  return (
    <div>
      <PageContainer>
        <PageHeader title="Signal Statistics" description="Platform-wide signal generation and outcome distribution." />
        <AdminComingSoon
          icon={TrendingUp}
          title="Signal statistics not yet available"
          description="An admin-wide signals/analytics endpoint hasn't been built yet - the existing GET /signals only returns the caller's own signals, not a cross-user aggregate."
        />
      </PageContainer>
    </div>
  );
}
