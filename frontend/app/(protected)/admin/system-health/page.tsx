"use client";

import { Activity, AlertTriangle, BrainCircuit, Newspaper, CalendarClock } from "lucide-react";

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
import { formatDateTime, formatEnumLabel } from "@/lib/format";
import type { IngestionHealthResponse } from "@/services/types";

/** Phase 9G (ADR-139): per-pipeline ingestion health card - a mock
 * provider must never look like a real one at a glance, so `uses_mock`
 * renders as a loud `warning` badge, not a quiet label. `last_error`
 * (if present) is the most recent run's failure, not historical - it
 * clears on the next success (`ingestion_health.record_success`). */
function IngestionHealthCard({
  label,
  icon: Icon,
  health,
}: {
  label: string;
  icon: typeof Newspaper;
  health: IngestionHealthResponse;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
          <Icon className="size-4 text-muted-foreground" />
          {label}
        </div>
        {health.uses_mock ? (
          <Badge variant="warning">Mock data</Badge>
        ) : (
          <Badge variant="success">Live provider</Badge>
        )}
      </div>
      <dl className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <dt className="text-muted-foreground">Provider(s)</dt>
          <dd className="font-medium text-foreground">{health.providers.join(", ") || "none"}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Last success</dt>
          <dd className="font-medium text-foreground">
            {health.last_success_at ? formatDateTime(health.last_success_at) : "never"}
          </dd>
        </div>
      </dl>
      {health.last_error ? (
        <div className="flex items-start gap-2 rounded-md bg-destructive/10 p-2 text-xs text-destructive">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
          <span className="break-words">{health.last_error}</span>
        </div>
      ) : null}
    </div>
  );
}

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
                <PanelHeader
                  title="Ingestion Health"
                  subtitle="News and Economic Calendar - provider, mock usage, last run"
                />
                <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2">
                  <IngestionHealthCard
                    label="News"
                    icon={Newspaper}
                    health={systemQuery.data.news}
                  />
                  <IngestionHealthCard
                    label="Economic Calendar"
                    icon={CalendarClock}
                    health={systemQuery.data.economic_calendar}
                  />
                </div>
              </Panel>
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
