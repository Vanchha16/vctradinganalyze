"use client";

import { useState } from "react";

import { FileClock } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader, Tag } from "@/components/shared/premium";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { AuditLogFilterBar, type AuditLogFilters } from "@/features/admin/components/audit-log-filter-bar";
import { AuditLogTable } from "@/features/admin/components/audit-log-table";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAdminLogs } from "@/hooks/use-admin-logs";
import type { AdminAuditLogResponse } from "@/services/types";

const DEFAULT_FILTERS: AuditLogFilters = {
  user_id: undefined,
  action: undefined,
  resource: undefined,
  from: undefined,
  to: undefined,
};

const PAGE_SIZE = 20;

/**
 * Real audit log viewer (Phase 8F, docs/59 §11, ADR-129) - replaces the
 * Phase 8D `AdminComingSoon` placeholder now that `GET /admin/logs`
 * exists. Server-side filtering/pagination (all real query params), no
 * client-side sort since the backend is always newest-first (ADR-129).
 * Read-only, so this page has no dialogs/mutations - `AuditLogTable` has
 * no row actions at all.
 */
export default function AdminAuditLogsPage() {
  const [filters, setFilters] = useState<AuditLogFilters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [actorLabel, setActorLabel] = useState<string | null>(null);

  const logsQuery = useAdminLogs({
    user_id: filters.user_id,
    action: filters.action,
    resource: filters.resource,
    from: filters.from,
    to: filters.to,
    page,
    limit: PAGE_SIZE,
  });

  const total = logsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = logsQuery.data?.items ?? [];

  function handleFilterChange(next: Partial<AuditLogFilters>) {
    if ("user_id" in next && next.user_id === undefined) setActorLabel(null);
    setFilters((prev) => ({ ...prev, ...next }));
    setPage(1);
  }

  function handleFilterByActor(log: AdminAuditLogResponse) {
    if (!log.user_id) return;
    setActorLabel(log.actor_username ?? log.actor_email ?? log.user_id.slice(0, 8));
    handleFilterChange({ user_id: log.user_id });
  }

  return (
    <div>
      <PageContainer>
        <PageHeader title="Audit Logs" description="A record of every administrative action." />

        <AuditLogFilterBar filters={filters} onChange={handleFilterChange} actorLabel={actorLabel} />

        <Panel>
          <PanelHeader
            title="All activity"
            subtitle={`${total} log${total === 1 ? "" : "s"}`}
            icon={<FileClock className="size-4" />}
            right={<Tag tone="brand">Live</Tag>}
          />
          {logsQuery.isLoading ? (
            <div className="p-4">
              <Skeleton className="h-96 w-full" />
            </div>
          ) : logsQuery.isError ? (
            <ErrorCard error={logsQuery.error} onRetry={() => logsQuery.refetch()} />
          ) : items.length > 0 ? (
            <>
              <AuditLogTable logs={items} onFilterByActor={handleFilterByActor} />
              <div className="px-5 pb-4">
                <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
              </div>
            </>
          ) : (
            <EmptyState
              icon={FileClock}
              title="No audit log entries found"
              description="Try a different filter, or check back after an admin action occurs."
            />
          )}
        </Panel>
      </PageContainer>
    </div>
  );
}
