"use client";

import Link from "next/link";
import { useState } from "react";

import { BarChart3, BookOpen, BrainCircuit, ExternalLink, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { Panel, PanelHeader, Tag } from "@/components/shared/premium";
import { PriceChart } from "@/components/shared/price-chart-lazy";
import { Button } from "@/components/ui/button";
import { useAiAnalysisHistory } from "@/hooks/use-ai-analysis-history";
import { useAssetDetail } from "@/hooks/use-asset-detail";
import { useCandles } from "@/hooks/use-candles";
import { useLatestCandle } from "@/hooks/use-latest-candle";
import { formatEnumLabel, formatPrice, formatRelativeTime } from "@/lib/format";
import type { Timeframe } from "@/services/types";

const RECOMMENDATION_TONE: Record<string, string> = { buy: "bull", sell: "bear" };

/**
 * The desktop Markets master-detail workspace's right rail (docs/56) -
 * every section is wired to the same real per-symbol hooks the
 * `/markets/[symbol]` route already uses (asset detail, candles, latest
 * close, AI analysis history). No bid/ask depth data exists anywhere in
 * this backend, so the Order Book section shows an honest "not
 * available" state rather than fabricated levels.
 */
export function MarketDetailPanel({ symbol }: { symbol: string | null }) {
  const [timeframe, setTimeframe] = useState<Timeframe>("h1");

  const assetQuery = useAssetDetail(symbol);
  const candlesQuery = useCandles(symbol, timeframe, 200);
  const latestQuery = useLatestCandle(symbol, timeframe);
  const aiHistoryQuery = useAiAnalysisHistory({ symbol: symbol ?? undefined, limit: 1 });

  if (!symbol || !assetQuery.data) {
    return (
      <Panel>
        <EmptyState
          icon={BarChart3}
          title="Select an instrument"
          description="Choose a row from the screener to preview its quote, chart and AI read here."
        />
      </Panel>
    );
  }

  const asset = assetQuery.data;
  const latestAnalysis = aiHistoryQuery.data?.items[0];
  const query = `?symbol=${asset.symbol}&timeframe=${timeframe}`;

  return (
    <div className="flex flex-col gap-4">
      <Panel>
        <PanelHeader
          title={`${asset.symbol} · ${asset.name}`}
          subtitle={formatEnumLabel(asset.market_type)}
          right={<Tag tone={asset.is_active ? "bull" : "muted"}>{asset.is_active ? "Active" : "Inactive"}</Tag>}
        />
        <div className="p-3">
          <PriceChart
            candles={candlesQuery.data?.items ?? []}
            timeframe={timeframe}
            onTimeframeChange={setTimeframe}
            isLoading={candlesQuery.isLoading}
          />
        </div>
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
          <div className="bg-card px-4 py-3">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Exchange</p>
            <p className="num mt-0.5 text-sm font-semibold">{asset.exchange ?? "—"}</p>
          </div>
          <div className="bg-card px-4 py-3">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Timeframe</p>
            <p className="num mt-0.5 text-sm font-semibold">{timeframe.toUpperCase()}</p>
          </div>
        </div>
        <div className="p-4 pt-0">
          <Link href={`/markets/${asset.symbol}`} className="focus-ring flex w-fit items-center gap-1.5 rounded-md text-xs font-medium text-muted-foreground transition-colors hover:text-primary">
            Open full page <ExternalLink className="size-3" />
          </Link>
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="AI summary" icon={<BrainCircuit className="size-4" />} />
        {aiHistoryQuery.isLoading ? null : latestAnalysis ? (
          <div className="p-4">
            <div className="flex items-center gap-2">
              <Tag tone={RECOMMENDATION_TONE[latestAnalysis.recommendation] ?? "muted"}>
                {latestAnalysis.recommendation.toUpperCase()}
              </Tag>
              <span className="text-[11px] text-muted-foreground">
                {Math.round(latestAnalysis.confidence_score)}% confidence · {formatRelativeTime(latestAnalysis.calculated_at)}
              </span>
            </div>
            <p className="mt-3 line-clamp-4 text-xs leading-relaxed text-muted-foreground">
              {latestAnalysis.reasoning.summary}
            </p>
            <Link
              href={`/ai-analysis/${latestAnalysis.id}`}
              className="focus-ring mt-3 flex w-fit items-center gap-1.5 rounded-md text-xs font-medium text-primary transition-colors hover:brightness-125"
            >
              View full analysis <ExternalLink className="size-3" />
            </Link>
          </div>
        ) : (
          <EmptyState
            icon={Sparkles}
            title="No AI analysis yet"
            description={`Generate a fresh read on ${asset.symbol} using the existing AI Analysis engine.`}
            action={
              <Button variant="brand" size="sm" asChild>
                <Link href={`/ai-analysis${query}`}>Generate AI Analysis</Link>
              </Button>
            }
          />
        )}
      </Panel>

      <Panel>
        <PanelHeader title="Order book" subtitle={`${asset.symbol} · level 2`} icon={<BookOpen className="size-4" />} />
        <EmptyState
          icon={BookOpen}
          title="Order book unavailable"
          description="This data provider doesn't supply Level 2 depth yet, so no bid/ask ladder is shown here."
        />
      </Panel>
    </div>
  );
}
