import { FileClock } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { AdminComingSoon } from "@/features/admin/components/admin-coming-soon";
import { PageContainer } from "@/features/dashboard/components/page-container";

/** `GET /admin/logs` was not built in Phase 8C (only `/admin/users*`
 * shipped) - `AuditLog` rows already exist for every admin action (Phase
 * 8C's `AdminUserService`), but there's no endpoint to read them yet. */
export default function AdminAuditLogsPage() {
  return (
    <div>
      <PageContainer>
        <PageHeader title="Audit Logs" description="A record of every administrative action." />
        <AdminComingSoon
          icon={FileClock}
          title="Audit log viewer not yet available"
          description="Every admin action (create, edit, disable, reset password, delete, role change) is already being recorded - a GET /admin/logs endpoint to read them back hasn't been built yet."
        />
      </PageContainer>
    </div>
  );
}
