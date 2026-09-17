"use client";

import { Activity, Info, Percent, Target, TrendingUp } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader } from "@/components/shared/premium";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { StatCard } from "@/features/admin/components/stat-card";
import {
  MEANINGFUL_SAMPLE,
  PerformanceTable,
  percent,
  points,
  ratio,
} from "@/features/admin/components/performance-table";
import { useAdminPerformance } from "@/hooks/use-admin-performance";
import { formatDate, formatDateTime } from "@/lib/format";

/**
 * ADR-174 - did the stored signals work?
 *
 * Read-only, computed per request, and deliberately narrow: it reports
 * what happened to signals this platform actually issued. It does not
 * re-adjudicate trades the monitor already settled, and it is not a
 * backtest of a strategy that was never run.
 *
 * Two things on this page are load-bearing and must not be "tidied away":
 * every rate carries its own denominator with a small-sample mark under
 * 30 trades, and the points note stays next to the totals. Both exist
 * because this project has already drawn a wrong conclusion from a small
 * sample read as if it were money.
 */
export default function AdminPerformancePage() {
  const query = useAdminPerformance();
  const data = query.data;
  const overall = data?.overall;

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="Signal Performance"
          description="What happened to the signals this platform issued - outcomes, fill rates and the risk review's record."
        />

        {query.isError ? (
          <ErrorCard error={query.error} onRetry={() => query.refetch()} />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
              <StatCard label="Filled trades" value={overall?.trades} icon={Activity} isLoading={query.isLoading} />
              <StatCard
                label="Win rate"
                value={overall ? percent(overall.win_rate) : undefined}
                icon={Percent}
                isLoading={query.isLoading}
              />
              <StatCard
                label="Total points"
                value={overall ? points(overall.total_points) : undefined}
                icon={TrendingUp}
                isLoading={query.isLoading}
              />
              <StatCard
                label="Expectancy"
                value={overall ? points(overall.expectancy) : undefined}
                icon={Target}
                isLoading={query.isLoading}
              />
              <StatCard
                label="Profit factor"
                value={overall ? ratio(overall.profit_factor) : undefined}
                icon={TrendingUp}
                isLoading={query.isLoading}
              />
            </div>

            {query.isLoading ? (
              <Skeleton className="h-96 w-full" />
            ) : data ? (
              <>
                <Panel>
                  <div className="flex flex-col gap-3 px-5 py-4">
                    <p className="flex items-start gap-2 text-[13px] text-muted-foreground">
                      <Info className="mt-0.5 size-4 shrink-0 text-warn" />
                      <span>{data.points_note}</span>
                    </p>
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                      <Badge variant="outline">Since {formatDate(data.epoch)}</Badge>
                      <span>
                        Signals created before this are excluded - they predate the fill gate and
                        carry outcomes current code cannot produce.
                      </span>
                    </div>
                    {overall && overall.trades < MEANINGFUL_SAMPLE ? (
                      <p className="text-[11px] text-warn">
                        {overall.trades} filled trade{overall.trades === 1 ? "" : "s"} in total -
                        not yet enough to conclude anything. The measurement is what turns waiting
                        into evidence.
                      </p>
                    ) : null}
                  </div>
                </Panel>

                <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <Panel>
                    <PanelHeader
                      title="Fills"
                      subtitle="How many signals became trades"
                    />
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Group</TableHead>
                          <TableHead className="text-right">Created</TableHead>
                          <TableHead className="text-right">Filled</TableHead>
                          <TableHead className="text-right">Fill rate</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        <TableRow>
                          <TableCell className="text-[13px] font-medium">All</TableCell>
                          <TableCell className="text-right tabular-nums">
                            {data.fills.created}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {data.fills.filled}
                          </TableCell>
                          <TableCell className="text-right tabular-nums">
                            {percent(data.fills.fill_rate)}
                          </TableCell>
                        </TableRow>
                        {data.fills_by_signal_type.map((row) => (
                          <TableRow key={row.key ?? "__null__"}>
                            <TableCell className="text-[13px]">
                              {(row.key ?? "Not recorded").toUpperCase()}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {row.metrics.created}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {row.metrics.filled}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              {percent(row.metrics.fill_rate)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Panel>

                  <Panel>
                    <PanelHeader
                      title="Open right now"
                      subtitle="By the status a reader sees, not the stored one"
                    />
                    <div className="grid grid-cols-2 gap-3 p-4">
                      {(
                        [
                          ["Active", data.open_state.active],
                          ["Expired unfilled", data.open_state.expired],
                          ["Live trades", data.open_state.triggered],
                          ["Closed, no outcome", data.open_state.closed],
                        ] as const
                      ).map(([label, value]) => (
                        <div key={label}>
                          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                            {label}
                          </p>
                          <p className="text-lg font-semibold tabular-nums">{value}</p>
                        </div>
                      ))}
                    </div>
                    <p className="border-t border-border/70 px-5 py-3 text-[11px] text-muted-foreground">
                      {data.closed_without_outcome} filled trade
                      {data.closed_without_outcome === 1 ? "" : "s"} reached neither target before
                      timing out. They count in Trades, and in neither wins nor losses - so wins
                      plus losses can be less than the trade count.
                    </p>
                  </Panel>
                </div>

                <PerformanceTable
                  title="By strategy"
                  subtitle="Which approach actually paid"
                  rows={data.by_strategy}
                  nullLabel="No strategy recorded"
                />
                <PerformanceTable
                  title="By timeframe"
                  rows={data.by_timeframe}
                />
                <PerformanceTable
                  title="By direction"
                  rows={data.by_signal_type}
                />
                <PerformanceTable
                  title="By confidence"
                  subtitle="Whether a higher score actually meant a better trade"
                  rows={data.by_confidence}
                  nullLabel="Outside every band"
                />
                <PerformanceTable
                  title="Risk review"
                  subtitle="Approve versus veto - the comparison that decides whether the review gets enforced"
                  rows={data.risk_review}
                  nullLabel="Review did not run"
                />

                <Panel>
                  <PanelHeader title="Replacements" subtitle="Newer confirmed signals taking over an unfilled one" />
                  <div className="flex flex-col gap-2 px-5 py-4">
                    <p className="text-lg font-semibold tabular-nums">
                      {data.replacements.signals_replaced}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      signal{data.replacements.signals_replaced === 1 ? "" : "s"} replaced before
                      filling
                    </p>
                    {!data.replacements.comparable ? (
                      <p className="flex items-start gap-2 text-[11px] text-warn">
                        <Info className="mt-0.5 size-3.5 shrink-0" />
                        <span>{data.replacements.note}</span>
                      </p>
                    ) : null}
                  </div>
                </Panel>

                <p className="text-center text-[11px] text-muted-foreground">
                  Computed at {formatDateTime(data.generated_at)}. Nothing here is stored or
                  cached - every figure is recomputed per request.
                </p>
              </>
            ) : null}
          </div>
        )}
      </PageContainer>
    </div>
  );
}
