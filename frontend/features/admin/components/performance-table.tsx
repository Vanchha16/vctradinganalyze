"use client";

import { Badge } from "@/components/ui/badge";
import { Panel, PanelHeader } from "@/components/shared/premium";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { PerformanceBreakdownRow } from "@/services/types";

/** Below this, a rate is noise. 28 filled trades exist in total, so most
 * rows here will be marked - that is the honest state of the data, and
 * ADR-174 chose to show it rather than hide the row. */
export const MEANINGFUL_SAMPLE = 30;

/** A null ratio means "undefined", not zero (ADR-174). Never render it as
 * 0%. */
export function percent(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

export function points(value: string | null): string {
  if (value === null) return "—";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "—";
  const rounded = parsed.toFixed(2);
  return parsed > 0 ? `+${rounded}` : rounded;
}

export function ratio(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

export function pointsTone(value: string | null): string {
  if (value === null) return "";
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed === 0) return "";
  return parsed > 0 ? "text-bull" : "text-bear";
}

/** A group with no value is a real group: a signal from before the
 * `strategy` column existed, or an analysis the risk review never ran
 * on. Named, never dropped. */
function keyLabel(key: string | null, nullLabel: string): string {
  return key === null ? nullLabel : key.toUpperCase();
}

/**
 * One breakdown of ADR-174's outcome metrics.
 *
 * Every row carries its own `trades` count, and any row under 30 trades
 * is visibly marked: a win rate over 3 trades and one over 300 render
 * identically otherwise, and this project has already drawn a wrong
 * conclusion from a small sample.
 */
export function PerformanceTable({
  title,
  subtitle,
  rows,
  nullLabel = "Not recorded",
}: {
  title: string;
  subtitle?: string;
  rows: PerformanceBreakdownRow[];
  nullLabel?: string;
}) {
  return (
    <Panel>
      <PanelHeader title={title} subtitle={subtitle} />
      {rows.length === 0 ? (
        <p className="px-5 py-4 text-[13px] text-muted-foreground">
          No filled trades in this breakdown yet.
        </p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Group</TableHead>
              <TableHead className="text-right">Trades</TableHead>
              <TableHead className="text-right">W / L</TableHead>
              <TableHead className="text-right">Win rate</TableHead>
              <TableHead className="text-right">Points</TableHead>
              <TableHead className="text-right">Expectancy</TableHead>
              <TableHead className="text-right">Profit factor</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.key ?? "__null__"}>
                <TableCell>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[13px] font-medium">{keyLabel(row.key, nullLabel)}</span>
                    {row.metrics.trades < MEANINGFUL_SAMPLE ? (
                      <Badge variant="outline" title={`Fewer than ${MEANINGFUL_SAMPLE} trades`}>
                        Small sample
                      </Badge>
                    ) : null}
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums">{row.metrics.trades}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {row.metrics.wins} / {row.metrics.losses}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {percent(row.metrics.win_rate)}
                </TableCell>
                <TableCell
                  className={cn("text-right tabular-nums", pointsTone(row.metrics.total_points))}
                >
                  {points(row.metrics.total_points)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {points(row.metrics.expectancy)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {ratio(row.metrics.profit_factor)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Panel>
  );
}
