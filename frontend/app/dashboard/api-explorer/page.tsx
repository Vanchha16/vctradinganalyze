"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { LoadingCard } from "@/features/dashboard/components/loading-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { RawResponsePanel } from "@/features/dashboard/components/raw-response-panel";
import { TopControls } from "@/features/dashboard/components/top-controls";
import { useDashboardSelection } from "@/hooks/use-dashboard-selection";
import { useMarketRegime } from "@/hooks/use-market-regime";
import { useSmcAnalysis } from "@/hooks/use-smc-analysis";
import { useTechnicalAnalysis } from "@/hooks/use-technical-analysis";

type Endpoint = "technical" | "smc" | "market-regime";

const ENDPOINT_LABELS: Record<Endpoint, string> = {
  technical: "GET /analysis/technical/{symbol}",
  smc: "GET /analysis/smc/{symbol}",
  "market-regime": "GET /analysis/market-regime/{symbol}",
};

export default function ApiExplorerPage() {
  const { symbol, timeframe } = useDashboardSelection();
  const [endpoint, setEndpoint] = useState<Endpoint>("technical");

  const technical = useTechnicalAnalysis(symbol, timeframe);
  const smc = useSmcAnalysis(symbol, timeframe);
  const regime = useMarketRegime(symbol, timeframe);

  const active = endpoint === "technical" ? technical : endpoint === "smc" ? smc : regime;

  return (
    <div>
      <TopControls onRefresh={() => active.refetch()} isFetching={active.isFetching} />
      <PageContainer>
        <div className="flex flex-col gap-4 xl:max-w-5xl">
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-muted-foreground">Endpoint</label>
            <Select value={endpoint} onValueChange={(value) => setEndpoint(value as Endpoint)}>
              <SelectTrigger className="w-72">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(ENDPOINT_LABELS) as Endpoint[]).map((key) => (
                  <SelectItem key={key} value={key}>
                    {ENDPOINT_LABELS[key]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {active.isLoading ? (
            <LoadingCard />
          ) : active.isError ? (
            <ErrorCard error={active.error} onRetry={() => active.refetch()} />
          ) : active.data ? (
            <Card>
              <CardHeader>
                <CardTitle>{ENDPOINT_LABELS[endpoint]}</CardTitle>
              </CardHeader>
              <CardContent>
                <RawResponsePanel data={active.data} />
                <div className="mt-3">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() =>
                      navigator.clipboard.writeText(JSON.stringify(active.data, null, 2))
                    }
                  >
                    Copy JSON
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </PageContainer>
    </div>
  );
}
