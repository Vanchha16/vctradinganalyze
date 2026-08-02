"use client";

import { ErrorCard } from "@/features/dashboard/components/error-card";
import { LoadingCard } from "@/features/dashboard/components/loading-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { RawResponsePanel } from "@/features/dashboard/components/raw-response-panel";
import { TechnicalAnalysisCard } from "@/features/dashboard/components/technical-analysis-card";
import { TopControls } from "@/features/dashboard/components/top-controls";
import { useDashboardSelection } from "@/hooks/use-dashboard-selection";
import { useTechnicalAnalysis } from "@/hooks/use-technical-analysis";

export default function TechnicalAnalysisPage() {
  const { symbol, timeframe } = useDashboardSelection();
  const technical = useTechnicalAnalysis(symbol, timeframe);

  return (
    <div>
      <TopControls onRefresh={() => technical.refetch()} isFetching={technical.isFetching} />
      <PageContainer>
        <div className="flex flex-col gap-4 xl:max-w-5xl">
          {technical.isLoading ? (
            <LoadingCard />
          ) : technical.isError ? (
            <ErrorCard error={technical.error} onRetry={() => technical.refetch()} />
          ) : technical.data ? (
            <>
              <TechnicalAnalysisCard data={technical.data} />
              <RawResponsePanel data={technical.data} />
            </>
          ) : null}
        </div>
      </PageContainer>
    </div>
  );
}
