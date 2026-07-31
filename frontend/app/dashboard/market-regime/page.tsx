"use client";

import { ErrorCard } from "@/features/dashboard/components/error-card";
import { LoadingCard } from "@/features/dashboard/components/loading-card";
import { MarketRegimeCard } from "@/features/dashboard/components/market-regime-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { RawResponsePanel } from "@/features/dashboard/components/raw-response-panel";
import { TopControls } from "@/features/dashboard/components/top-controls";
import { useDashboardSelection } from "@/hooks/use-dashboard-selection";
import { useMarketRegime } from "@/hooks/use-market-regime";

export default function MarketRegimePage() {
  const { symbol, timeframe } = useDashboardSelection();
  const regime = useMarketRegime(symbol, timeframe);

  return (
    <div>
      <TopControls onRefresh={() => regime.refetch()} isFetching={regime.isFetching} />
      <PageContainer>
        <div className="flex flex-col gap-4 xl:max-w-5xl">
          {regime.isLoading ? (
            <LoadingCard />
          ) : regime.isError ? (
            <ErrorCard error={regime.error} onRetry={() => regime.refetch()} />
          ) : regime.data ? (
            <>
              <MarketRegimeCard data={regime.data} />
              <RawResponsePanel data={regime.data} />
            </>
          ) : null}
        </div>
      </PageContainer>
    </div>
  );
}
