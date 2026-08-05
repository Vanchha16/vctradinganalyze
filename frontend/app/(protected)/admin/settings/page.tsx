import { Settings } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { AdminComingSoon } from "@/features/admin/components/admin-coming-soon";
import { PageContainer } from "@/features/dashboard/components/page-container";

/** Explicitly requested as a placeholder if the backend isn't ready - it
 * isn't: `SystemSetting` (the table) exists since Phase 1, but no
 * `/admin/settings` CRUD route was built in Phase 8C. */
export default function AdminSettingsPage() {
  return (
    <div>
      <PageContainer>
        <PageHeader title="Admin Settings" description="Platform-wide configuration." />
        <AdminComingSoon
          icon={Settings}
          title="Admin settings not yet available"
          description="The underlying SystemSetting table already exists, but no admin-facing CRUD endpoint has been built on top of it yet."
        />
      </PageContainer>
    </div>
  );
}
