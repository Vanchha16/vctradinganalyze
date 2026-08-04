"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/shared/page-header";
import { PriceChart } from "@/components/shared/price-chart-lazy";
import { SmcOverlayToggles } from "@/components/shared/smc-overlay-toggles";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { BookmarkButton } from "@/features/signals/components/bookmark-button";
import { SignalStatusTimeline } from "@/features/signals/components/signal-status-timeline";
import { EvidenceList } from "@/features/ai-analysis/components/evidence-list";
import { ReasoningSections } from "@/features/ai-analysis/components/reasoning-sections";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAiAnalysis } from "@/hooks/use-ai-analysis";
import { useCandles } from "@/hooks/use-candles";
import { useSignal } from "@/hooks/use-signal";
import { useSmcAnalysis } from "@/hooks/use-smc-analysis";
import { recommendationVariant, signalStatusVariant } from "@/lib/badge-variants";
import { formatEnumLabel, formatPrice } from "@/lib/format";
import { buildSmcOverlays, DEFAULT_SMC_OVERLAYS, type SmcOverlayKind } from "@/lib/smc-overlays";
import type { Timeframe } from "@/services/types";

export default function SignalDetailPage() {
  const params = useParams<{ id: string }>();
  const signalQuery = useSignal(params.id);
  const analysisQuery = useAiAnalysis(signalQuery.data?.analysis_id ?? null);
  const [chartTimeframe, setChartTimeframe] = useState<Timeframe | null>(null);
  const [enabledOverlays, setEnabledOverlays] = useState<Set<SmcOverlayKind>>(new Set(DEFAULT_SMC_OVERLAYS));

  const effectiveTimeframe = chartTimeframe ?? signalQuery.data?.timeframe ?? null;
  const candlesQuery = useCandles(signalQuery.data?.symbol ?? null, effectiveTimeframe, 300);
  const smcQuery = useSmcAnalysis(signalQuery.data?.symbol ?? null, effectiveTimeframe);

  function toggleOverlay(kind: SmcOverlayKind) {
    setEnabledOverlays((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  }

  if (signalQuery.isLoading) {
    return (
      <PageContainer>
        <Skeleton className="h-64 w-full" />
      </PageContainer>
    );
  }

  if (signalQuery.isError || !signalQuery.data) {
    return (
      <PageContainer>
        <ErrorCard error={signalQuery.error} onRetry={() => signalQuery.refetch()} />
      </PageContainer>
    );
  }

  const signal = signalQuery.data;
  const smcOverlays = buildSmcOverlays(smcQuery.data, enabledOverlays);
  const chartOverlays = [
    { price: Number(signal.entry_price), color: "#3B82F6", title: "Entry" },
    { price: Number(signal.stop_loss), color: "#EF4444", title: "Stop Loss" },
    { price: Number(signal.take_profit), color: "#22C55E", title: "Take Profit" },
    ...smcOverlays.lines,
  ];

  return (
    <div>
      <PageHeader
        title={`${signal.symbol} · ${signal.timeframe.toUpperCase()}`}
        description="Signal detail"
        actions={<BookmarkButton signalId={signal.id} />}
      />
      <PageContainer>
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle>Trade Setup</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant={recommendationVariant(signal.signal_type)}>
                    {signal.signal_type.toUpperCase()}
                  </Badge>
                  <Badge variant={signalStatusVariant(signal.status)}>{formatEnumLabel(signal.status)}</Badge>
                </div>
                <dl className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <dt className="text-xs text-muted-foreground">Entry</dt>
                    <dd className="font-medium tabular-nums">{formatPrice(signal.entry_price)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Confidence</dt>
                    <dd className="font-medium tabular-nums">{signal.confidence.toFixed(0)}%</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Stop Loss</dt>
                    <dd className="font-medium tabular-nums">{formatPrice(signal.stop_loss)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Risk/Reward</dt>
                    <dd className="font-medium tabular-nums">1:{signal.risk_reward.toFixed(2)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Take Profit</dt>
                    <dd className="font-medium tabular-nums">{formatPrice(signal.take_profit)}</dd>
                  </div>
                </dl>
                <div className="border-t border-border pt-4">
                  <SignalStatusTimeline signal={signal} />
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Reasoning</CardTitle>
              </CardHeader>
              <CardContent>
                {analysisQuery.isLoading ? (
                  <Skeleton className="h-40 w-full" />
                ) : analysisQuery.isError || !analysisQuery.data ? (
                  <p className="text-sm text-muted-foreground">Reasoning unavailable.</p>
                ) : (
                  <ReasoningSections reasoning={analysisQuery.data.reasoning} />
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardContent className="flex flex-col gap-3 pt-4">
              <SmcOverlayToggles enabled={enabledOverlays} onToggle={toggleOverlay} />
              {effectiveTimeframe ? (
                <PriceChart
                  candles={candlesQuery.data?.items ?? []}
                  overlays={chartOverlays}
                  zones={smcOverlays.zones}
                  markers={smcOverlays.markers}
                  timeframe={effectiveTimeframe}
                  onTimeframeChange={setChartTimeframe}
                  isLoading={candlesQuery.isLoading}
                />
              ) : null}
            </CardContent>
          </Card>

          {analysisQuery.data ? (
            <EvidenceList
              supportingEvidence={analysisQuery.data.supporting_evidence}
              conflictingEvidence={analysisQuery.data.conflicting_evidence}
              risks={analysisQuery.data.risks}
              invalidationConditions={analysisQuery.data.invalidation_conditions}
            />
          ) : null}
        </div>
      </PageContainer>
    </div>
  );
}
