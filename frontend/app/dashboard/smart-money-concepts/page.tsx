"use client";

import { ErrorCard } from "@/features/dashboard/components/error-card";
import { LoadingCard } from "@/features/dashboard/components/loading-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { RawResponsePanel } from "@/features/dashboard/components/raw-response-panel";
import { SmcCard } from "@/features/dashboard/components/smc-card";
import { TopControls } from "@/features/dashboard/components/top-controls";
import { useDashboardSelection } from "@/hooks/use-dashboard-selection";
import { useSmcAnalysis } from "@/hooks/use-smc-analysis";

export default function SmartMoneyConceptsPage() {
  const { symbol, timeframe } = useDashboardSelection();
  const smc = useSmcAnalysis(symbol, timeframe);

  return (
    <div>
      <TopControls onRefresh={() => smc.refetch()} isFetching={smc.isFetching} />
      <PageContainer>
        <div className="flex flex-col gap-4 xl:max-w-5xl">
          {smc.isLoading ? (
            <LoadingCard />
          ) : smc.isError ? (
            <ErrorCard error={smc.error} onRetry={() => smc.refetch()} />
          ) : smc.data ? (
            <>
              <SmcCard data={smc.data} />
              <RawResponsePanel data={smc.data} />
            </>
          ) : null}
        </div>
      </PageContainer>
    </div>
  );
}
