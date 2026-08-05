import { Server } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { AdminComingSoon } from "@/features/admin/components/admin-coming-soon";
import { PageContainer } from "@/features/dashboard/components/page-container";

/** `GET /admin/system` was not built in Phase 8C. Even once it exists, per
 * docs/59 §10.1/ADR-116 it will only ever report `/health`/`/health/ready`
 * liveness + simple counts, never live CPU/memory/queue telemetry - no
 * metrics infrastructure exists anywhere in this project (BACKLOG.md §3). */
export default function AdminSystemHealthPage() {
  return (
    <div>
      <PageContainer>
        <PageHeader title="System Health" description="Database, Redis, and service liveness." />
        <AdminComingSoon
          icon={Server}
          title="System health view not yet available"
          description="GET /admin/system hasn't been built yet. It will reuse the existing /health and /health/ready liveness checks plus simple counts - real CPU/queue-depth telemetry is a separate, larger effort (BACKLOG.md §3)."
        />
      </PageContainer>
    </div>
  );
}
