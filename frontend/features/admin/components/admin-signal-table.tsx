"use client";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { recommendationVariant, signalStatusVariant } from "@/lib/badge-variants";
import { formatDateTime, formatEnumLabel, formatPrice } from "@/lib/format";
import type { SignalResponse } from "@/services/types";

/** Read-only admin view over `GET /admin/signals` (docs/58 §3.2, ADR-130,
 * Phase 7D-D) - modeled on `UserTable`/`AuditLogTable`'s shape (a plain
 * `Table` composition, `Badge` + the existing `lib/badge-variants`
 * mappings), no row actions since this is a read-only surface. `Signal`
 * has no `user_id` (ADR-130), so there is no "owner" column to show. */
export function AdminSignalTable({ signals }: { signals: SignalResponse[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Timeframe</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Entry</TableHead>
          <TableHead>Stop Loss</TableHead>
          <TableHead>Take Profit</TableHead>
          <TableHead>R/R</TableHead>
          <TableHead>Confidence</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {signals.map((signal) => (
          <TableRow key={signal.id}>
            <TableCell className="font-semibold">{signal.symbol}</TableCell>
            <TableCell className="text-muted-foreground">{signal.timeframe.toUpperCase()}</TableCell>
            <TableCell>
              <Badge variant={recommendationVariant(signal.signal_type)}>
                {signal.signal_type.toUpperCase()}
              </Badge>
            </TableCell>
            <TableCell className="tabular-nums">{formatPrice(signal.entry_price)}</TableCell>
            <TableCell className="tabular-nums">{formatPrice(signal.stop_loss)}</TableCell>
            <TableCell className="tabular-nums">{formatPrice(signal.take_profit)}</TableCell>
            <TableCell className="tabular-nums">1:{signal.risk_reward.toFixed(2)}</TableCell>
            <TableCell className="tabular-nums">{signal.confidence.toFixed(0)}%</TableCell>
            <TableCell>
              <Badge variant={signalStatusVariant(signal.status)}>{formatEnumLabel(signal.status)}</Badge>
            </TableCell>
            <TableCell className="whitespace-nowrap text-muted-foreground">
              {formatDateTime(signal.created_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
