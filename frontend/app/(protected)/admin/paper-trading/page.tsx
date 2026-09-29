"use client";

import { FlaskConical } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Panel } from "@/components/shared/premium";
import { Skeleton } from "@/components/ui/skeleton";
import { PaperSwingReport } from "@/features/admin/components/paper-swing-report";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAuth } from "@/hooks/use-auth";
import { usePaperSwingStatistics } from "@/hooks/use-paper-swing";

/**
 * ADR-182 - the swing strategy's paper-trading record on EURUSD, GBPUSD and
 * USDJPY. Super admin only, like Strategy Settings; the backend enforces
 * it, this page only explains instead of showing a 403. Starting and
 * pausing the run is the "Swing paper trading" switch in Strategy Settings.
 */
export default function PaperTradingPage() {
  const { user, status } = useAuth();
  const isSuperAdmin = user?.role === "super_admin";
  const query = usePaperSwingStatistics(isSuperAdmin);

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="Paper Trading"
          description="Swing strategy on EURUSD, GBPUSD and USDJPY - D1 trend, H4 pullback. Recorded only, never sent to the EA."
        />
        {status !== "authenticated" || (isSuperAdmin && query.isLoading) ? (
          <Skeleton className="h-96 w-full" />
        ) : !isSuperAdmin ? (
          <Panel>
            <EmptyState
              icon={FlaskConical}
              title="Super admin only"
              description="This record decides whether the strategy is ever traded with real money, so only the account owner can see it."
            />
          </Panel>
        ) : query.isError ? (
          <ErrorCard error={query.error} onRetry={() => query.refetch()} />
        ) : query.data ? (
          <PaperSwingReport data={query.data} />
        ) : null}
      </PageContainer>
    </div>
  );
}
