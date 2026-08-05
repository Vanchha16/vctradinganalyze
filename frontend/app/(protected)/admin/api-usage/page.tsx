import { Terminal } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { AdminComingSoon } from "@/features/admin/components/admin-coming-soon";
import { PageContainer } from "@/features/dashboard/components/page-container";

/** No request-metrics collection exists anywhere in this project
 * (BACKLOG.md §3's `GET /metrics` gap). ADR-124 proposed a labeled
 * AI-analysis/signal-count usage proxy for a future Admin phase - not
 * built here, since Phase 8D's approved scope was `/admin/users*`
 * frontend only. */
export default function AdminApiUsagePage() {
  return (
    <div>
      <PageContainer>
        <PageHeader title="API Usage" description="Request volume and usage patterns." />
        <AdminComingSoon
          icon={Terminal}
          title="API usage metrics not yet available"
          description="No request-metrics infrastructure exists in this project yet (BACKLOG.md §3). ADR-124 proposes a labeled AI-analysis/signal-count proxy as a future step - not a substitute for real telemetry."
        />
      </PageContainer>
    </div>
  );
}
