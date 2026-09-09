"use client";

import { useState } from "react";

import { Radio } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Panel } from "@/components/shared/premium";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { TradingViewAlertTable } from "@/features/admin/components/tradingview-alert-table";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useTradingViewAlerts } from "@/hooks/use-tradingview-alerts";

const PAGE_SIZE = 50;

/**
 * Read side for `GET /admin/tradingview-alerts` (ADR-146).
 *
 * These are **not** signals. They arrive from an external Pine indicator
 * over a public webhook, carry no stop or take-profit, and never reach
 * the signal or trade-execution paths. The page says so on screen rather
 * than leaving an operator to infer it from a table that otherwise looks
 * a lot like the signals list.
 */
export default function AdminTradingViewAlertsPage() {
  const [page, setPage] = useState(1);
  const alertsQuery = useTradingViewAlerts({ page, limit: PAGE_SIZE });
  const items = alertsQuery.data?.items ?? [];

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="TradingView Alerts"
          description="Inbound webhook alerts from the Pine Script indicators."
        />

        <div className="flex flex-col gap-6">
          <p className="text-xs leading-relaxed text-muted-foreground">
            These come from an external TradingView indicator, not this project&apos;s AI analysis.
            They carry no stop loss or take profit, they do not create signals, and they never reach
            trade execution — they are recorded and forwarded to Telegram only. The Pine scripts&apos;
            own README notes their output will not agree with the backend&apos;s signal engine.
          </p>

          {alertsQuery.isError ? (
            <ErrorCard error={alertsQuery.error} onRetry={() => alertsQuery.refetch()} />
          ) : alertsQuery.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : items.length === 0 ? (
            <EmptyState
              icon={Radio}
              title="No alerts received yet"
              description="Alerts appear here once TRADINGVIEW_WEBHOOK_SECRET is set and a TradingView alert is pointed at the webhook URL. Until then the endpoint returns 404."
            />
          ) : (
            <>
              <Panel className="p-5">
                <TradingViewAlertTable alerts={items} />
              </Panel>
              <Pagination
                page={page}
                totalPages={Math.max(1, Math.ceil((alertsQuery.data?.total ?? 0) / PAGE_SIZE))}
                onPageChange={setPage}
              />
            </>
          )}
        </div>
      </PageContainer>
    </div>
  );
}
