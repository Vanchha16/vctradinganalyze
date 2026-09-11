"use client";

import { Bot } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader, Tag } from "@/components/shared/premium";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { EaActivityFilterBar, type EaActivityFilters } from "@/features/ea/components/ea-activity-filter-bar";
import { EaEventTable } from "@/features/ea/components/ea-event-table";
import { useAuth } from "@/hooks/use-auth";
import { useEaEvents } from "@/hooks/use-ea-events";

const PAGE_SIZE = 25;

/**
 * Everything the MT5 Expert Advisor reported (ADR-162), newest first -
 * "what has my bot been doing?" without opening MT5. Super admin only,
 * matching who can hold an EA token (ADR-161); the backend enforces it,
 * this page just explains instead of showing a 403.
 */
export default function EaActivityPage() {
  const { user, status } = useAuth();
  const [filters, setFilters] = useState<EaActivityFilters>({ mode: "all" });
  const [page, setPage] = useState(1);
  const isSuperAdmin = user?.role === "super_admin";

  const eventsQuery = useEaEvents(
    {
      dry_run: filters.mode === "all" ? undefined : filters.mode === "dry",
      event_type: filters.eventType,
      page,
      limit: PAGE_SIZE,
    },
    isSuperAdmin,
  );

  const total = eventsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = eventsQuery.data?.items ?? [];

  function handleFilterChange(next: Partial<EaActivityFilters>) {
    setFilters((prev) => ({ ...prev, ...next }));
    setPage(1);
  }

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="EA Activity"
          description="What your MT5 Expert Advisor did with each signal - checks, orders, fills and closes."
        />

        {status !== "authenticated" ? (
          <Skeleton className="h-96 w-full" />
        ) : !isSuperAdmin ? (
          <Panel>
            <EmptyState
              icon={Bot}
              title="Super admin only"
              description="EA activity belongs to the account holding the EA token."
            />
          </Panel>
        ) : (
          <>
            <EaActivityFilterBar filters={filters} onChange={handleFilterChange} />
            <Panel>
              <PanelHeader
                title="All activity"
                subtitle={`${total} event${total === 1 ? "" : "s"}`}
                icon={<Bot className="size-4" />}
                right={<Tag tone="brand">Live</Tag>}
              />
              {eventsQuery.isLoading ? (
                <div className="p-4">
                  <Skeleton className="h-96 w-full" />
                </div>
              ) : eventsQuery.isError ? (
                <ErrorCard error={eventsQuery.error} onRetry={() => eventsQuery.refetch()} />
              ) : items.length > 0 ? (
                <>
                  <EaEventTable events={items} />
                  <div className="px-5 pb-4">
                    <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
                  </div>
                </>
              ) : (
                <EmptyState
                  icon={Bot}
                  title="No EA activity yet"
                  description="Events appear here once your Expert Advisor acts on a signal. Dry-run checks count too."
                />
              )}
            </Panel>
          </>
        )}
      </PageContainer>
    </div>
  );
}
