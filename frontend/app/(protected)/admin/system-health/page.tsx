"use client";

import { Activity, BrainCircuit } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader } from "@/components/shared/premium";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MaintenanceActionsPanel } from "@/features/admin/components/maintenance-actions";
import { StatCard } from "@/features/admin/components/stat-card";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAdminSystemStatus } from "@/hooks/use-admin-system-status";
import { systemStatusVariant } from "@/lib/badge-variants";
import { formatEnumLabel } from "@/lib/format";

/** Real data from `GET /admin/system` (docs/58 §3.2, ADR-116/ADR-130,
 * Phase 7D-D) - replaces the Phase 8D `AdminComingSoon` placeholder.
 * `database`/`redis` come back as `"ok"`/`"down"` in a 200 response, never
 * an HTTP error - a down dependency is rendered as normal data here, not
 * treated as a failed request (`systemQuery.isError` only fires for an
 * actual network/auth failure). */
export default function AdminSystemHealthPage() {
  const systemQuery = useAdminSystemStatus();

  return (
    <div>
      <PageContainer>
        <PageHeader title="System Health" description="Database, Redis, and service liveness." />

        {systemQuery.isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : systemQuery.isError ? (
          <ErrorCard error={systemQuery.error} onRetry={() => systemQuery.refetch()} />
        ) : systemQuery.data ? (
          <>
            <Panel className="p-4">
              <div className="flex flex-wrap items-center gap-3">
                <Badge variant={systemStatusVariant(systemQuery.data.database)}>
                  Database: {formatEnumLabel(systemQuery.data.database)}
                </Badge>
                <Badge variant={systemStatusVariant(systemQuery.data.redis)}>
                  Redis: {formatEnumLabel(systemQuery.data.redis)}
                </Badge>
              </div>
            </Panel>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
              <StatCard
                label="Signals Today"
                value={systemQuery.data.signals_today}
                icon={Activity}
                isLoading={false}
              />
              <StatCard
                label="AI Analyses Today"
                value={systemQuery.data.ai_analyses_today}
                icon={BrainCircuit}
                isLoading={false}
              />
            </div>

            <div className="mt-4">
              <Panel>
                <PanelHeader title="Maintenance" subtitle="Manually trigger a data refresh" />
                <div className="p-4">
                  <MaintenanceActionsPanel />
                </div>
              </Panel>
            </div>

            <p className="mt-4 text-center text-[11px] text-muted-foreground">
              This is liveness plus today&rsquo;s activity counts, not full telemetry - there is no
              CPU, memory, or queue-depth data. Real observability is tracked separately
              (BACKLOG.md §3).
            </p>
          </>
        ) : null}
      </PageContainer>
    </div>
  );
}
