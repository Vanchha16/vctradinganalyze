"use client";

import { useState } from "react";

import { TrendingUp, Users as UsersIcon } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader } from "@/components/shared/premium";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { AdminSignalTable } from "@/features/admin/components/admin-signal-table";
import { SignalTypeDistributionBar } from "@/features/admin/components/signal-type-distribution-bar";
import { StatCard } from "@/features/admin/components/stat-card";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAdminAnalytics } from "@/hooks/use-admin-analytics";
import { useAdminSignals } from "@/hooks/use-admin-signals";

const PAGE_SIZE = 20;

/**
 * Real data from `GET /admin/signals` + `GET /admin/analytics` (docs/58
 * §3.2, ADR-130, Phase 7D-D) - replaces the Phase 8D `AdminComingSoon`
 * placeholder. `signal_type_distribution` renders as a plain CSS
 * proportion bar, not a chart (ADR-131 - the analytics payload is four
 * scalars and a ~2-key dictionary, not the richer docs/25 §15 set the
 * original chart-library assumption was scoped for).
 *
 * `Signal` has no `user_id` column at all (confirmed in Phase 7D-C,
 * ADR-130) - `GET /admin/signals` is scope-identical to the public
 * `GET /signals`, not a "this user's signals only" surface unlocked here.
 */
export default function AdminSignalStatisticsPage() {
  const [page, setPage] = useState(1);
  const analyticsQuery = useAdminAnalytics();
  const signalsQuery = useAdminSignals({ page, limit: PAGE_SIZE });

  const total = signalsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = signalsQuery.data?.items ?? [];

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="Signal Statistics"
          description="Platform-wide signal generation and outcome distribution."
        />

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <StatCard
            label="Daily Active Users"
            value={analyticsQuery.data?.daily_active_users}
            icon={UsersIcon}
            isLoading={analyticsQuery.isLoading}
          />
          <Panel className="p-4">
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              Signal Type Distribution
            </p>
            {analyticsQuery.isLoading ? (
              <Skeleton className="h-8 w-full" />
            ) : analyticsQuery.data ? (
              <SignalTypeDistributionBar distribution={analyticsQuery.data.signal_type_distribution} />
            ) : (
              <p className="text-[11px] text-muted-foreground">Unavailable.</p>
            )}
          </Panel>
        </div>

        <div className="mt-4">
          <Panel>
            <PanelHeader
              title="All signals"
              subtitle={`${total} signal${total === 1 ? "" : "s"}`}
              icon={<TrendingUp className="size-4" />}
            />
            {signalsQuery.isLoading ? (
              <div className="p-4">
                <Skeleton className="h-96 w-full" />
              </div>
            ) : signalsQuery.isError ? (
              <ErrorCard error={signalsQuery.error} onRetry={() => signalsQuery.refetch()} />
            ) : items.length > 0 ? (
              <>
                <AdminSignalTable signals={items} />
                <div className="px-5 pb-4">
                  <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
                </div>
              </>
            ) : (
              <EmptyState
                icon={TrendingUp}
                title="No signals yet"
                description="Signals will appear here once generated, on-demand or by the hourly watchlist job."
              />
            )}
          </Panel>
        </div>
      </PageContainer>
    </div>
  );
}
