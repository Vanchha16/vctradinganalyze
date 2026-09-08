"use client";

import { AlertTriangle, Clock, Gauge, Terminal } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader } from "@/components/shared/premium";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiUsageTable } from "@/features/admin/components/api-usage-table";
import { StatCard } from "@/features/admin/components/stat-card";
import { StatusClassBar } from "@/features/admin/components/status-class-bar";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAdminApiUsage } from "@/hooks/use-admin-api-usage";

/**
 * Real data from `GET /admin/api-usage` (ADR-144), folding the Prometheus
 * counters ADR-136 has collected since Phase 9D.
 *
 * Replaces a placeholder whose copy claimed "no request-metrics
 * infrastructure exists in this project yet" - true when Phase 8D wrote
 * it, false since Phase 9D, and still on screen a month later.
 *
 * **Everything here is cumulative since the API process started.** There
 * is no time series: Prometheus keeps history in the scraping *server*,
 * and this project runs none. So no trend lines, no rate-per-minute, and
 * every number resets on restart/deploy. The page says so in as many
 * words rather than letting a reader assume otherwise.
 */
export default function AdminApiUsagePage() {
  const usageQuery = useAdminApiUsage();
  const data = usageQuery.data;
  const isLoading = usageQuery.isLoading;

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="API Usage"
          description="Request volume, error rates and latency, measured since the API last restarted."
        />

        {usageQuery.isError ? (
          <ErrorCard error={usageQuery.error} onRetry={() => usageQuery.refetch()} />
        ) : (
          <div className="flex flex-col gap-6">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label="Requests"
                value={data?.total_requests}
                icon={Terminal}
                isLoading={isLoading}
              />
              <StatCard
                label="Errors (4xx + 5xx)"
                value={data?.total_errors}
                icon={AlertTriangle}
                isLoading={isLoading}
              />
              <StatCard
                label="Avg latency (ms)"
                value={
                  data?.avg_latency_ms === null || data?.avg_latency_ms === undefined
                    ? undefined
                    : Math.round(data.avg_latency_ms)
                }
                icon={Clock}
                isLoading={isLoading}
              />
              <StatCard
                label="Routes seen"
                value={data?.route_count}
                icon={Gauge}
                isLoading={isLoading}
              />
            </div>

            <Panel className="p-5">
              <PanelHeader title="Response status" />
              {isLoading ? (
                <Skeleton className="h-16 w-full" />
              ) : (
                <StatusClassBar
                  counts={[
                    { label: "2xx", value: data?.status_2xx ?? 0, className: "bg-emerald-500" },
                    { label: "3xx", value: data?.status_3xx ?? 0, className: "bg-sky-500" },
                    { label: "4xx", value: data?.status_4xx ?? 0, className: "bg-amber-500" },
                    { label: "5xx", value: data?.status_5xx ?? 0, className: "bg-rose-500" },
                  ]}
                />
              )}
            </Panel>

            <Panel className="p-5">
              <PanelHeader title="By route" />
              {isLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : data && data.routes.length > 0 ? (
                <ApiUsageTable routes={data.routes} />
              ) : (
                <p className="text-sm text-muted-foreground">
                  No requests recorded yet since the API last restarted.
                </p>
              )}
            </Panel>

            <p className="text-xs leading-relaxed text-muted-foreground">
              These are cumulative counters since the API process last started, not a time series —
              every value resets on restart or deploy. Latency percentiles are approximated from
              Prometheus histogram buckets, so they are bucket-width accurate rather than exact. For
              trends over time, scrape <code className="font-mono">GET /api/v1/metrics</code> with a
              real Prometheus server.
            </p>
          </div>
        )}
      </PageContainer>
    </div>
  );
}
