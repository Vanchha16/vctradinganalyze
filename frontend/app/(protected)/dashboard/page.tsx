"use client";

import { useSearchParams } from "next/navigation";

import { ErrorCard } from "@/features/dashboard/components/error-card";
import { LoadingCard } from "@/features/dashboard/components/loading-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { SummaryCard } from "@/features/dashboard/components/summary-card";
import { TopControls } from "@/features/dashboard/components/top-controls";
import { useDashboardSelection } from "@/hooks/use-dashboard-selection";
import { useMarketRegime } from "@/hooks/use-market-regime";
import { useSmcAnalysis } from "@/hooks/use-smc-analysis";
import { useTechnicalAnalysis } from "@/hooks/use-technical-analysis";

const TREND_VARIANT = { bullish: "success", bearish: "destructive", sideways: "secondary" } as const;
const STRUCTURE_VARIANT = { bullish: "success", bearish: "destructive", range: "secondary", transition: "secondary" } as const;
const REGIME_VARIANT = {
  trending_bullish: "success",
  trending_bearish: "destructive",
  ranging: "secondary",
  accumulation: "secondary",
  distribution: "secondary",
  breakout: "warning",
  pullback: "warning",
  reversal: "warning",
  high_volatility: "warning",
  low_volatility: "secondary",
  uncertain: "secondary",
} as const;

export default function DashboardOverviewPage() {
  const { symbol, timeframe } = useDashboardSelection();
  const searchParams = useSearchParams();
  const query = searchParams.toString();
  const withQuery = (href: string) => (query ? `${href}?${query}` : href);

  const technical = useTechnicalAnalysis(symbol, timeframe);
  const smc = useSmcAnalysis(symbol, timeframe);
  const regime = useMarketRegime(symbol, timeframe);

  const isFetching = technical.isFetching || smc.isFetching || regime.isFetching;
  const handleRefresh = () => {
    void technical.refetch();
    void smc.refetch();
    void regime.refetch();
  };

  return (
    <div>
      <TopControls onRefresh={handleRefresh} isFetching={isFetching} />
      <PageContainer>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
          {technical.isLoading ? (
            <LoadingCard />
          ) : technical.isError ? (
            <ErrorCard error={technical.error} onRetry={() => technical.refetch()} />
          ) : technical.data ? (
            <SummaryCard
              title="Technical Analysis"
              href={withQuery("/dashboard/technical-analysis")}
              value={technical.data.technical_score.toFixed(1)}
              valueLabel="Technical Score"
              badges={[
                { label: technical.data.trend, variant: TREND_VARIANT[technical.data.trend] },
                { label: technical.data.strength.replace("_", " "), variant: "outline" },
              ]}
              facts={[
                { label: "Support", value: technical.data.support ? technical.data.support.price : "—" },
                { label: "Resistance", value: technical.data.resistance ? technical.data.resistance.price : "—" },
              ]}
            />
          ) : null}

          {smc.isLoading ? (
            <LoadingCard />
          ) : smc.isError ? (
            <ErrorCard error={smc.error} onRetry={() => smc.refetch()} />
          ) : smc.data ? (
            <SummaryCard
              title="Smart Money Concepts"
              href={withQuery("/dashboard/smart-money-concepts")}
              value={smc.data.smc_score.toFixed(1)}
              valueLabel="SMC Score"
              badges={[
                { label: smc.data.market_structure.state, variant: STRUCTURE_VARIANT[smc.data.market_structure.state] },
                { label: smc.data.premium_discount.position, variant: "outline" },
              ]}
              facts={[
                { label: "Order Blocks", value: smc.data.order_blocks.length },
                { label: "Fair Value Gaps", value: smc.data.fair_value_gaps.length },
              ]}
            />
          ) : null}

          {regime.isLoading ? (
            <LoadingCard />
          ) : regime.isError ? (
            <ErrorCard error={regime.error} onRetry={() => regime.refetch()} />
          ) : regime.data ? (
            <SummaryCard
              title="Market Regime"
              href={withQuery("/dashboard/market-regime")}
              value={`${regime.data.confidence.toFixed(1)}%`}
              valueLabel="Confidence"
              badges={[
                { label: regime.data.regime.replace("_", " "), variant: REGIME_VARIANT[regime.data.regime] },
                { label: `${regime.data.volatility.state.replace("_", " ")} volatility`, variant: "outline" },
              ]}
              facts={[
                { label: "Trend Strength", value: regime.data.trend_regime.strength.replace("_", " ") },
                { label: "Volatility", value: regime.data.volatility.state.replace("_", " ") },
              ]}
            />
          ) : null}
        </div>
      </PageContainer>
    </div>
  );
}
