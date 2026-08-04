"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/shared/page-header";
import { SymbolTimeframePicker } from "@/components/shared/symbol-timeframe-picker";
import { Button } from "@/components/ui/button";
import { Pagination } from "@/components/ui/pagination";
import { CardSkeleton } from "@/components/shared/skeletons";
import { SignalCard } from "@/features/signals/components/signal-card";
import { SignalFilterBar, type SignalFilters } from "@/features/signals/components/signal-filter-bar";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useGenerateSignal } from "@/hooks/use-generate-signal";
import { useQueryFilters } from "@/hooks/use-query-filters";
import { useSignals } from "@/hooks/use-signals";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { SignalStatus, Timeframe } from "@/services/types";
import { EmptyState } from "@/components/shared/empty-state";
import { TrendingUp } from "lucide-react";

const DEFAULT_FILTERS: SignalFilters = { status: undefined, symbol: undefined };

export default function SignalsPage() {
  const { filters, page, setFilters, setPage } = useQueryFilters(DEFAULT_FILTERS);
  const searchParams = useSearchParams();
  const [symbol, setSymbol] = useState<string | null>(searchParams.get("symbol"));
  const [timeframe, setTimeframe] = useState<Timeframe>((searchParams.get("timeframe") as Timeframe) || "h1");

  const signalsQuery = useSignals({
    status: filters.status as SignalStatus | undefined,
    symbol: filters.symbol,
    page,
    limit: 20,
  });
  const generateSignal = useGenerateSignal();

  async function handleGenerate() {
    if (!symbol) return;
    try {
      const result = await generateSignal.mutateAsync({ symbol, timeframe });
      if (result.signal) {
        toast.success(`New ${result.signal.signal_type.toUpperCase()} signal generated for ${symbol}.`);
      } else {
        toast.info(`Recommendation is WAIT for ${symbol} - no signal generated.`);
      }
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error(message);
    }
  }

  const total = signalsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div>
      <PageHeader title="Signals" description="AI-generated trade signals, derived from persisted analyses." />
      <div className="flex flex-wrap items-end justify-between gap-4 px-4 pt-4 sm:px-6 lg:px-8">
        <SymbolTimeframePicker
          symbol={symbol}
          timeframe={timeframe}
          onSymbolChange={setSymbol}
          onTimeframeChange={setTimeframe}
        />
        <Button onClick={() => void handleGenerate()} disabled={!symbol || generateSignal.isPending}>
          {generateSignal.isPending ? "Generating..." : "Generate Signal"}
        </Button>
      </div>
      <SignalFilterBar filters={filters} onChange={(next) => setFilters(next)} />
      <PageContainer>
        {signalsQuery.isLoading ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <CardSkeleton key={index} />
            ))}
          </div>
        ) : signalsQuery.isError ? (
          <ErrorCard error={signalsQuery.error} onRetry={() => signalsQuery.refetch()} />
        ) : signalsQuery.data && signalsQuery.data.items.length > 0 ? (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {signalsQuery.data.items.map((signal) => (
                <SignalCard key={signal.id} signal={signal} />
              ))}
            </div>
            <div className="pt-4">
              <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
            </div>
          </>
        ) : (
          <EmptyState
            icon={TrendingUp}
            title="No signals yet"
            description="Generate a signal above for any asset to get started."
          />
        )}
      </PageContainer>
    </div>
  );
}
