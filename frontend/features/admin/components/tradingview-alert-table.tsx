"use client";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime } from "@/lib/format";
import type { TradingViewAlertResponse } from "@/services/types";

/** Read-only, like `AuditLogTable` - nothing mutates an alert after the
 *  webhook stores it, and there is deliberately no action to replay one
 *  into the signal pipeline (ADR-146). */
export function TradingViewAlertTable({ alerts }: { alerts: TradingViewAlertResponse[] }) {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Received</TableHead>
            <TableHead>Symbol</TableHead>
            <TableHead>Direction</TableHead>
            <TableHead>Timeframe</TableHead>
            <TableHead className="text-right">Price</TableHead>
            <TableHead className="text-right">Score</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Telegram</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {alerts.map((alert) => (
            <TableRow key={alert.id}>
              <TableCell className="whitespace-nowrap text-muted-foreground">
                {formatDateTime(alert.created_at)}
              </TableCell>
              <TableCell className="font-medium">
                {alert.symbol}
                {alert.exchange ? (
                  <span className="ml-1 text-xs text-muted-foreground">{alert.exchange}</span>
                ) : null}
              </TableCell>
              <TableCell>
                <Badge variant={alert.direction === "buy" ? "success" : "destructive"}>
                  {alert.direction.toUpperCase()}
                </Badge>
              </TableCell>
              {/* TradingView's own interval string, shown verbatim - "60"
                  means 60 minutes in their vocabulary, not this project's. */}
              <TableCell className="text-muted-foreground">{alert.timeframe ?? "—"}</TableCell>
              <TableCell className="text-right tabular-nums">
                {alert.entry_price ?? "—"}
              </TableCell>
              <TableCell className="text-right tabular-nums text-muted-foreground">
                {alert.score !== null ? alert.score.toFixed(1) : "—"}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {alert.source ?? "—"}
              </TableCell>
              <TableCell>
                {alert.delivered_at ? (
                  <span className="text-xs text-muted-foreground">
                    {formatDateTime(alert.delivered_at)}
                  </span>
                ) : (
                  // Not an error state: it usually means no Telegram
                  // account is linked. Saying "Not sent" is honest;
                  // a red failure badge would overstate it.
                  <span className="text-xs text-muted-foreground">Not sent</span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
