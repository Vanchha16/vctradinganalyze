"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/shared/page-header";
import { PriceChart } from "@/components/shared/price-chart-lazy";
import { SmcOverlayToggles } from "@/components/shared/smc-overlay-toggles";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AnalysisSummary } from "@/features/ai-analysis/components/analysis-summary";
import { EvidenceList } from "@/features/ai-analysis/components/evidence-list";
import { ReasoningSections } from "@/features/ai-analysis/components/reasoning-sections";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAiAnalysis } from "@/hooks/use-ai-analysis";
import { useCandles } from "@/hooks/use-candles";
import { useSmcAnalysis } from "@/hooks/use-smc-analysis";
import { buildSmcOverlays, DEFAULT_SMC_OVERLAYS, type SmcOverlayKind } from "@/lib/smc-overlays";
import type { Timeframe } from "@/services/types";

export default function AiAnalysisDetailPage() {
  const params = useParams<{ id: string }>();
  const analysisQuery = useAiAnalysis(params.id);
  const [chartTimeframe, setChartTimeframe] = useState<Timeframe | null>(null);
  const [enabledOverlays, setEnabledOverlays] = useState<Set<SmcOverlayKind>>(new Set(DEFAULT_SMC_OVERLAYS));

  const effectiveTimeframe = chartTimeframe ?? analysisQuery.data?.timeframe ?? null;
  const candlesQuery = useCandles(analysisQuery.data?.symbol ?? null, effectiveTimeframe, 300);
  const smcQuery = useSmcAnalysis(analysisQuery.data?.symbol ?? null, effectiveTimeframe);

  function toggleOverlay(kind: SmcOverlayKind) {
    setEnabledOverlays((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  }

  if (analysisQuery.isLoading) {
    return (
      <PageContainer>
        <Skeleton className="h-96 w-full" />
      </PageContainer>
    );
  }

  if (analysisQuery.isError || !analysisQuery.data) {
    return (
      <PageContainer>
        <ErrorCard error={analysisQuery.error} onRetry={() => analysisQuery.refetch()} />
      </PageContainer>
    );
  }

  const analysis = analysisQuery.data;

  return (
    <div>
      <PageHeader title={`${analysis.symbol} · ${analysis.timeframe.toUpperCase()}`} description="AI Analysis" />
      <PageContainer>
        <div className="flex flex-col gap-6">
          <AnalysisSummary analysis={analysis} />

          <Card>
            <CardContent className="flex flex-col gap-3 pt-4">
              <SmcOverlayToggles enabled={enabledOverlays} onToggle={toggleOverlay} />
              {effectiveTimeframe
                ? (() => {
                    const smcOverlays = buildSmcOverlays(smcQuery.data, enabledOverlays);
                    const overlays = [
                      ...(analysis.entry_price
                        ? [
                            { price: Number(analysis.entry_price), color: "#3B82F6", title: "Entry" },
                            ...(analysis.stop_loss
                              ? [{ price: Number(analysis.stop_loss), color: "#EF4444", title: "Stop Loss" }]
                              : []),
                            ...(analysis.take_profit
                              ? [{ price: Number(analysis.take_profit), color: "#22C55E", title: "Take Profit" }]
                              : []),
                          ]
                        : []),
                      ...smcOverlays.lines,
                    ];
                    return (
                      <PriceChart
                        candles={candlesQuery.data?.items ?? []}
                        overlays={overlays}
                        zones={smcOverlays.zones}
                        markers={smcOverlays.markers}
                        timeframe={effectiveTimeframe}
                        onTimeframeChange={setChartTimeframe}
                        isLoading={candlesQuery.isLoading}
                      />
                    );
                  })()
                : null}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-4">
              <ReasoningSections reasoning={analysis.reasoning} />
            </CardContent>
          </Card>

          <EvidenceList
            supportingEvidence={analysis.supporting_evidence}
            conflictingEvidence={analysis.conflicting_evidence}
            risks={analysis.risks}
            invalidationConditions={analysis.invalidation_conditions}
          />
        </div>
      </PageContainer>
    </div>
  );
}
