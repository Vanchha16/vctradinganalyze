"use client";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { orderStatusVariant } from "@/lib/badge-variants";
import { formatDateTime, formatEnumLabel, formatPrice } from "@/lib/format";
import type { BrokerOrderResponse } from "@/services/types";

/** Read-only admin view over `GET /admin/orders` (EA Bot spec §3F) -
 * every real order the bot has ever placed on the operator's live
 * Exness account, no row actions (view-only this phase, same as
 * `AdminSignalTable`'s shape). Empty by default: nothing appears here
 * until `EXECUTION_ENABLED=true` and a signal is actually executed. */
export function AdminOrderTable({ orders }: { orders: BrokerOrderResponse[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Symbol</TableHead>
          <TableHead>Volume</TableHead>
          <TableHead>Requested Price</TableHead>
          <TableHead>Filled Price</TableHead>
          <TableHead>Stop Loss</TableHead>
          <TableHead>Take Profit</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Broker Order ID</TableHead>
          <TableHead>Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {orders.map((order) => (
          <TableRow key={order.id}>
            <TableCell className="font-semibold">{order.symbol}</TableCell>
            <TableCell className="tabular-nums">{order.volume}</TableCell>
            <TableCell className="tabular-nums">{formatPrice(order.requested_price)}</TableCell>
            <TableCell className="tabular-nums">
              {order.filled_price ? formatPrice(order.filled_price) : "—"}
            </TableCell>
            <TableCell className="tabular-nums">{formatPrice(order.stop_loss)}</TableCell>
            <TableCell className="tabular-nums">{formatPrice(order.take_profit)}</TableCell>
            <TableCell>
              <Badge variant={orderStatusVariant(order.status)}>{formatEnumLabel(order.status)}</Badge>
              {order.rejection_reason ? (
                <p className="mt-1 text-xs text-muted-foreground">{order.rejection_reason}</p>
              ) : null}
            </TableCell>
            <TableCell className="text-muted-foreground">{order.broker_order_id ?? "—"}</TableCell>
            <TableCell className="whitespace-nowrap text-muted-foreground">
              {formatDateTime(order.created_at)}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
