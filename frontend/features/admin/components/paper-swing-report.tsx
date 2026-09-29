"use client";

import { useState } from "react";

import {
  Panel,
  PanelHeader,
  Segmented,
  Tag,
} from "@/components/shared/premium";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usePaperSwingTrades } from "@/hooks/use-paper-swing";
import { cn } from "@/lib/utils";
import type {
  PaperSwingStatisticsResponse,
  PaperSwingSummary,
  PaperSwingTrade,
} from "@/services/types";

/** ADR-182: the paper record is judged at 8-12 weeks. Below this many
 * closed trades, a win rate is not evidence of anything. */
const MEANINGFUL_TRADES = 30;
const PAGE_SIZE = 25;

const REJECT_LABELS: Record<string, string> = {
  rr_below_min: "R:R below 2",
  stop_below_min: "Stop tighter than 0.5 ATR",
  no_room: "Target/stop on the wrong side",
  trade_open: "Pair already had a trade open",
};

function r(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "—";
  const fixed = value.toFixed(digits);
  return value > 0 ? `+${fixed}R` : `${fixed}R`;
}

function tone(value: number | null | undefined): string {
  if (!value) return "";
  return value > 0 ? "text-bull" : "text-bear";
}

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${value.toFixed(1)}%`;
}

function num(value: string | null, digits: number): string {
  if (value === null) return "—";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "—";
}

function when(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * ADR-182 - the swing strategy's paper record next to the backtest it is
 * judged against. Read only: nothing here can reach the EA.
 */
export function PaperSwingReport({
  data,
}: {
  data: PaperSwingStatisticsResponse;
}) {
  const { overall } = data;
  const reference = data.backtest_reference;

  return (
    <div className="flex flex-col gap-4">
      <Panel>
        <PanelHeader
          title="Paper vs backtest"
          subtitle={`Rules ${data.strategy_version}, frozen for the paper period. Results are net of spread and swap, in R (1R = the risk of the trade).`}
          right={
            <Tag tone={data.enabled ? "bull" : "muted"}>
              {data.enabled ? "Running" : "Paused"}
            </Tag>
          }
        />
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead />
                <TableHead className="text-right">Trades</TableHead>
                <TableHead className="text-right">Win rate</TableHead>
                <TableHead className="text-right">Avg / trade</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead className="text-right">Max drawdown</TableHead>
                <TableHead className="text-right">Profit factor</TableHead>
                <TableHead className="text-right">Trades / week</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow className="font-semibold">
                <TableCell>Paper</TableCell>
                <TableCell className="text-right tabular-nums">
                  {overall.trades}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {pct(overall.win_rate)}
                </TableCell>
                <TableCell
                  className={cn("text-right tabular-nums", tone(overall.avg_r))}
                >
                  {r(overall.avg_r)}
                </TableCell>
                <TableCell
                  className={cn(
                    "text-right tabular-nums",
                    tone(overall.total_r),
                  )}
                >
                  {r(overall.total_r, 1)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {overall.max_drawdown_r.toFixed(1)}R
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {overall.profit_factor?.toFixed(2) ?? "—"}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {data.trades_per_week?.toFixed(2) ?? "—"}
                </TableCell>
              </TableRow>
              {(
                [
                  [
                    "Backtest, Twelve Data candles (same as paper)",
                    reference.twelve_data,
                  ],
                  [
                    "Backtest, broker MT5 candles (ADR-181, reference)",
                    reference.mt5,
                  ],
                ] as const
              ).map(([label, ref]) => (
                <TableRow key={label} className="text-muted-foreground">
                  <TableCell>{label}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {ref.trades}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {pct(ref.win_rate)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {r(ref.avg_r)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {r(ref.total_r, 1)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {ref.max_drawdown_r.toFixed(1)}R
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {ref.profit_factor.toFixed(2)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {ref.trades_per_week.toFixed(2)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <p className="border-border/70 border-t px-5 py-3 text-[11px] text-muted-foreground">
          {data.started_at
            ? `Running ${data.weeks_running} weeks since ${when(data.started_at)}. `
            : "No setup recorded yet. "}
          {overall.open > 0
            ? `${overall.open} trade${overall.open === 1 ? "" : "s"} open. `
            : ""}
          {overall.trades < MEANINGFUL_TRADES
            ? `Only ${overall.trades} closed trade${overall.trades === 1 ? "" : "s"} - at about 0.86 a week, 8-12 weeks gives 7-10, too few to confirm or rule out the edge on their own.`
            : ""}
        </p>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <BreakdownPanel title="By pair" rows={data.by_pair} />
        <BreakdownPanel title="By direction" rows={data.by_direction} />
      </div>

      <Panel>
        <PanelHeader
          title="Setups not taken"
          subtitle="Every candidate is recorded. The filters are the backtest's, unchanged."
        />
        <div className="flex flex-wrap gap-2 px-5 py-4">
          {Object.entries(data.rejected).map(([reason, count]) => (
            <Tag key={reason}>
              {REJECT_LABELS[reason] ?? reason}: {count}
            </Tag>
          ))}
          <Tag>
            {REJECT_LABELS.trade_open}: {data.skipped_trade_open}
          </Tag>
        </div>
      </Panel>

      <TradeTable />
    </div>
  );
}

function BreakdownPanel({
  title,
  rows,
}: {
  title: string;
  rows: Record<string, PaperSwingSummary>;
}) {
  return (
    <Panel>
      <PanelHeader title={title} />
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead />
            <TableHead className="text-right">Trades</TableHead>
            <TableHead className="text-right">W / L</TableHead>
            <TableHead className="text-right">Total</TableHead>
            <TableHead className="text-right">Avg hold</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Object.entries(rows).map(([key, row]) => (
            <TableRow key={key}>
              <TableCell className="font-medium">{key.toUpperCase()}</TableCell>
              <TableCell className="text-right tabular-nums">
                {row.trades}
                {row.open ? (
                  <span className="text-muted-foreground">
                    {" "}
                    +{row.open} open
                  </span>
                ) : null}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {row.wins} / {row.losses}
                {row.timeouts ? (
                  <span className="text-muted-foreground">
                    {" "}
                    ({row.timeouts} t/o)
                  </span>
                ) : null}
              </TableCell>
              <TableCell
                className={cn("text-right tabular-nums", tone(row.total_r))}
              >
                {r(row.total_r, 1)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {row.avg_holding_hours === null
                  ? "—"
                  : `${row.avg_holding_hours.toFixed(0)}h`}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Panel>
  );
}

const STATUS_FILTERS = ["Trades", "All setups"] as const;

function statusTone(status: PaperSwingTrade["status"]): string {
  if (status === "win") return "bull";
  if (status === "loss") return "bear";
  if (status === "open") return "info";
  if (status === "timeout") return "warn";
  return "muted";
}

function TradeTable() {
  const [filter, setFilter] =
    useState<(typeof STATUS_FILTERS)[number]>("Trades");
  const [page, setPage] = useState(0);
  const query = usePaperSwingTrades(
    {
      status: filter === "Trades" ? "taken" : undefined,
      offset: page * PAGE_SIZE,
      limit: PAGE_SIZE,
    },
    true,
  );
  const total = query.data?.total ?? 0;

  return (
    <Panel>
      <PanelHeader
        title="Record"
        subtitle="Entry at the close of the H4 bar that confirmed the pullback. ADR = average daily range, 14 days."
        right={
          <Segmented
            options={[...STATUS_FILTERS]}
            value={filter}
            onChange={(v) => {
              setFilter(v as (typeof STATUS_FILTERS)[number]);
              setPage(0);
            }}
          />
        }
      />
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Signal</TableHead>
              <TableHead>Pair</TableHead>
              <TableHead>Side</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Entry</TableHead>
              <TableHead className="text-right">Stop</TableHead>
              <TableHead className="text-right">Target</TableHead>
              <TableHead className="text-right">Risk</TableHead>
              <TableHead className="text-right">R:R</TableHead>
              <TableHead className="text-right">ADR</TableHead>
              <TableHead className="text-right">Result</TableHead>
              <TableHead className="text-right">Held</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {query.data?.items.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={12}
                  className="py-8 text-center text-muted-foreground"
                >
                  Nothing recorded yet. Setups are checked every four hours.
                </TableCell>
              </TableRow>
            ) : null}
            {query.data?.items.map((t) => {
              const digits = t.symbol === "USDJPY" ? 3 : 5;
              const result = t.result_r === null ? null : Number(t.result_r);
              return (
                <TableRow key={t.id}>
                  <TableCell className="whitespace-nowrap tabular-nums">
                    {when(t.signal_time)}
                  </TableCell>
                  <TableCell className="font-medium">{t.symbol}</TableCell>
                  <TableCell
                    className={
                      t.direction === "buy" ? "text-bull" : "text-bear"
                    }
                  >
                    {t.direction.toUpperCase()}
                  </TableCell>
                  <TableCell>
                    <Tag tone={statusTone(t.status)}>{t.status}</Tag>
                    {t.reject_reason ? (
                      <span className="ml-1 text-[11px] text-muted-foreground">
                        {REJECT_LABELS[t.reject_reason] ?? t.reject_reason}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {num(t.entry_price, digits)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {num(t.stop_loss, digits)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {num(t.take_profit, digits)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {num(t.risk_pips, 1)}p
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {num(t.risk_reward, 2)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {t.adr_pips === null ? "—" : `${num(t.adr_pips, 0)}p`}
                  </TableCell>
                  <TableCell
                    className={cn("text-right tabular-nums", tone(result))}
                  >
                    {r(result)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {t.holding_hours === null
                      ? "—"
                      : `${num(t.holding_hours, 0)}h`}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
      {total > PAGE_SIZE ? (
        <div className="border-border/70 flex items-center justify-between border-t px-5 py-3 text-[12px] text-muted-foreground">
          <span>
            {page * PAGE_SIZE + 1}-{Math.min(total, (page + 1) * PAGE_SIZE)} of{" "}
            {total}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={(page + 1) * PAGE_SIZE >= total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </Panel>
  );
}
