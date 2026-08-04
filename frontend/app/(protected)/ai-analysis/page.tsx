"use client";

import { motion } from "framer-motion";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { SymbolTimeframePicker } from "@/components/shared/symbol-timeframe-picker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ListItemSkeleton } from "@/components/shared/skeletons";
import { AnalysisGuideStepper } from "@/features/ai-analysis/components/analysis-guide-stepper";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAiAnalysisHistory } from "@/hooks/use-ai-analysis-history";
import { useGenerateAiAnalysis } from "@/hooks/use-generate-ai-analysis";
import { recommendationVariant } from "@/lib/badge-variants";
import { formatRelativeTime } from "@/lib/format";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { Timeframe } from "@/services/types";
import { Sparkles } from "lucide-react";

export default function AiAnalysisPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [symbol, setSymbol] = useState<string | null>(searchParams.get("symbol"));
  const [timeframe, setTimeframe] = useState<Timeframe>((searchParams.get("timeframe") as Timeframe) || "h1");

  const generate = useGenerateAiAnalysis();
  const historyQuery = useAiAnalysisHistory({ limit: 20 });

  async function handleGenerate() {
    if (!symbol) return;
    try {
      const result = await generate.mutateAsync({ symbol, timeframe });
      router.push(`/ai-analysis/${result.id}`);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error(message);
    }
  }

  return (
    <div>
      <PageHeader title="AI Analysis" description="Generate a full AI-narrated market analysis for any asset." />
      <AnalysisGuideStepper step={generate.isPending ? 2 : symbol ? 2 : 1} />
      <motion.div
        key={generate.isPending ? "generating" : "idle"}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.15 }}
        className="flex flex-wrap items-end justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8"
      >
        <SymbolTimeframePicker
          symbol={symbol}
          timeframe={timeframe}
          onSymbolChange={setSymbol}
          onTimeframeChange={setTimeframe}
        />
        <Button onClick={() => void handleGenerate()} disabled={!symbol || generate.isPending}>
          {generate.isPending ? "Analyzing..." : "Generate Analysis"}
        </Button>
      </motion.div>
      <PageContainer>
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Recent History</p>
        {historyQuery.isLoading ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <ListItemSkeleton key={index} />
            ))}
          </div>
        ) : historyQuery.isError ? (
          <ErrorCard error={historyQuery.error} onRetry={() => historyQuery.refetch()} />
        ) : historyQuery.data && historyQuery.data.items.length > 0 ? (
          <div className="flex flex-col gap-2">
            {historyQuery.data.items.map((item) => (
              <Card key={item.id} interactive onClick={() => router.push(`/ai-analysis/${item.id}`)}>
                <CardContent className="flex items-center justify-between gap-4 py-3">
                  <div className="flex items-center gap-3">
                    <span className="font-medium">{item.symbol}</span>
                    <span className="text-xs text-muted-foreground">{item.timeframe.toUpperCase()}</span>
                    <Badge variant={recommendationVariant(item.recommendation)}>
                      {item.recommendation.toUpperCase()}
                    </Badge>
                  </div>
                  <span className="text-xs text-muted-foreground">{formatRelativeTime(item.calculated_at)}</span>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <EmptyState
            icon={Sparkles}
            title="No analyses yet"
            description="Select an asset above and generate your first AI analysis."
          />
        )}
      </PageContainer>
    </div>
  );
}
