"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { BrainCircuit, Gauge, LineChart as LineChartIcon, TrendingUp, Waves } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader, Tag } from "@/components/shared/premium";
import { PriceChart } from "@/components/shared/price-chart-lazy";
import type { PriceLineOverlay } from "@/components/shared/price-chart";
import { SmcOverlayToggles } from "@/components/shared/smc-overlay-toggles";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAssetDetail } from "@/hooks/use-asset-detail";
import { useCandles } from "@/hooks/use-candles";
import { useLatestCandle } from "@/hooks/use-latest-candle";
import { useSmcAnalysis } from "@/hooks/use-smc-analysis";
import { useTechnicalAnalysis } from "@/hooks/use-technical-analysis";
import { formatEnumLabel, formatPrice } from "@/lib/format";
import { buildSmcOverlays, DEFAULT_SMC_OVERLAYS, type SmcOverlayKind } from "@/lib/smc-overlays";
import type { Timeframe } from "@/services/types";

export default function MarketDetailPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = params.symbol.toUpperCase();
  const [timeframe, setTimeframe] = useState<Timeframe>("h1");
  const [enabledOverlays, setEnabledOverlays] = useState<Set<SmcOverlayKind>>(new Set(DEFAULT_SMC_OVERLAYS));

  const assetQuery = useAssetDetail(symbol);
  const candlesQuery = useCandles(symbol, timeframe, 300);
  const latestQuery = useLatestCandle(symbol, timeframe);
  const technicalQuery = useTechnicalAnalysis(symbol, timeframe);
  const smcQuery = useSmcAnalysis(symbol, timeframe);

  function toggleOverlay(kind: SmcOverlayKind) {
    setEnabledOverlays((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  }

  if (assetQuery.isLoading) {
    return (
      <PageContainer>
        <Skeleton className="h-96 w-full" />
      </PageContainer>
    );
  }

  if (assetQuery.isError || !assetQuery.data) {
    return (
      <PageContainer>
        <ErrorCard error={assetQuery.error} onRetry={() => assetQuery.refetch()} />
      </PageContainer>
    );
  }

  const asset = assetQuery.data;
  const overlays: PriceLineOverlay[] = [];
  if (technicalQuery.data?.support) {
    overlays.push({ price: Number(technicalQuery.data.support.price), color: "#22C55E", title: "Support" });
  }
  if (technicalQuery.data?.resistance) {
    overlays.push({ price: Number(technicalQuery.data.resistance.price), color: "#EF4444", title: "Resistance" });
  }
  const smcOverlays = buildSmcOverlays(smcQuery.data, enabledOverlays);
  overlays.push(...smcOverlays.lines);

  const query = `?symbol=${symbol}&timeframe=${timeframe}`;

  return (
    <div>
      <PageContainer>
        <PageHeader
          title={`${asset.symbol} · ${asset.name}`}
          description={formatEnumLabel(asset.market_type)}
          actions={<Tag tone={asset.is_active ? "bull" : "muted"}>{asset.is_active ? "Active" : "Inactive"}</Tag>}
        />
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1.6fr_1fr]">
          <Panel>
            <PanelHeader
              title={`${asset.symbol} · ${asset.name}`}
              subtitle={formatEnumLabel(asset.market_type)}
              icon={<TrendingUp className="size-4" />}
            />
            <div className="flex flex-col gap-3 p-4">
              <SmcOverlayToggles enabled={enabledOverlays} onToggle={toggleOverlay} />
              {candlesQuery.isError ? (
                <ErrorCard
                  error={candlesQuery.error}
                  onRetry={() => candlesQuery.refetch()}
                  notFoundHint="This asset likely has no candle data yet for the selected timeframe."
                />
              ) : (
                <PriceChart
                  candles={candlesQuery.data?.items ?? []}
                  overlays={overlays}
                  zones={smcOverlays.zones}
                  markers={smcOverlays.markers}
                  timeframe={timeframe}
                  onTimeframeChange={setTimeframe}
                  isLoading={candlesQuery.isLoading}
                />
              )}
            </div>
          </Panel>

          <div className="flex flex-col gap-4">
            <Panel>
              <PanelHeader title="Quote" subtitle={`${asset.symbol} · real-time`} />
              <div className="grid grid-cols-2 gap-px border-t border-border bg-border/60">
                <div className="bg-card px-4 py-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Latest close</p>
                  <p className="num mt-0.5 text-sm font-semibold">{formatPrice(latestQuery.data?.close)}</p>
                </div>
                <div className="bg-card px-4 py-3">
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Base / Quote</p>
                  <p className="num mt-0.5 text-sm font-semibold">
                    {asset.base_currency ?? "—"} / {asset.quote_currency ?? "—"}
                  </p>
                </div>
              </div>
            </Panel>

            <Panel className="flex flex-col gap-2 p-4">
              <Button variant="outline" size="sm" className="justify-start" asChild>
                <Link href={`/dashboard/technical-analysis${query}`}>
                  <LineChartIcon className="mr-2 size-3.5" /> View Technical Analysis
                </Link>
              </Button>
              <Button variant="outline" size="sm" className="justify-start" asChild>
                <Link href={`/dashboard/smart-money-concepts${query}`}>
                  <Waves className="mr-2 size-3.5" /> View Smart Money Concepts
                </Link>
              </Button>
              <Button variant="outline" size="sm" className="justify-start" asChild>
                <Link href={`/dashboard/market-regime${query}`}>
                  <Gauge className="mr-2 size-3.5" /> View Market Regime
                </Link>
              </Button>
              <Button variant="brand" size="sm" className="justify-start" asChild>
                <Link href={`/ai-analysis${query}`}>
                  <BrainCircuit className="mr-2 size-3.5" /> Generate AI Analysis
                </Link>
              </Button>
            </Panel>
          </div>
        </div>
      </PageContainer>
    </div>
  );
}
