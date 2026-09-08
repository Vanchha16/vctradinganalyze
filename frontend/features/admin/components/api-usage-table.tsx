"use client";

import { useMemo, useState } from "react";

import { ArrowDown, ArrowUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ApiUsageRouteResponse } from "@/services/types";

type SortKey = "requests" | "error_rate" | "avg_latency_ms" | "p95_latency_ms";

const COLUMNS: { key: SortKey; label: string }[] = [
  { key: "requests", label: "Requests" },
  { key: "error_rate", label: "Error rate" },
  { key: "avg_latency_ms", label: "Avg" },
  { key: "p95_latency_ms", label: "p95" },
];

function formatMs(value: number | null): string {
  // `null` is meaningful, not missing: either no latency was observed, or
  // the percentile fell in the +Inf bucket. An em dash says "no number to
  // report" rather than implying zero.
  if (value === null) return "—";
  if (value >= 1000) return `${(value / 1000).toFixed(2)} s`;
  return `${Math.round(value)} ms`;
}

/** Read-only, like `AuditLogTable` - nothing here is mutable. Sorted
 *  client-side: the whole snapshot arrives in one response (one row per
 *  method/route-template pair, cardinality-bounded by ADR-136), so there
 *  is no pagination and no server round-trip per sort. */
export function ApiUsageTable({ routes }: { routes: ApiUsageRouteResponse[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("requests");

  const sorted = useMemo(() => {
    return [...routes].sort((a, b) => {
      // Nulls always sort last regardless of key - a route with no
      // latency data is not "the fastest".
      const left = a[sortKey];
      const right = b[sortKey];
      if (left === null && right === null) return 0;
      if (left === null) return 1;
      if (right === null) return -1;
      return right - left;
    });
  }, [routes, sortKey]);

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Route</TableHead>
            <TableHead>Method</TableHead>
            {COLUMNS.map((column) => (
              <TableHead key={column.key} className="text-right">
                <button
                  type="button"
                  onClick={() => setSortKey(column.key)}
                  className="ml-auto flex items-center gap-1 hover:text-foreground"
                >
                  {column.label}
                  {sortKey === column.key ? (
                    <ArrowDown className="size-3" />
                  ) : (
                    <ArrowUp className="size-3 opacity-0" />
                  )}
                </button>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((route) => (
            <TableRow key={`${route.method}:${route.route}`}>
              <TableCell className="font-mono text-xs">
                {route.route === "unmatched" ? (
                  // Not a real route: ADR-136 collapses every unrouted
                  // path here. A large or growing count means something
                  // is probing the API, which is worth making visible
                  // rather than blending in with the rest.
                  <span className="flex items-center gap-2">
                    <Badge variant="outline">unmatched</Badge>
                    <span className="text-muted-foreground">no route — probes / typos</span>
                  </span>
                ) : (
                  route.route
                )}
              </TableCell>
              <TableCell>
                <Badge variant="outline">{route.method}</Badge>
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {route.requests.toLocaleString()}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                <span
                  className={
                    route.error_rate >= 0.5
                      ? "text-destructive"
                      : route.error_rate > 0
                        ? "text-foreground"
                        : "text-muted-foreground"
                  }
                >
                  {(route.error_rate * 100).toFixed(1)}%
                </span>
              </TableCell>
              <TableCell className="text-right tabular-nums text-muted-foreground">
                {formatMs(route.avg_latency_ms)}
              </TableCell>
              <TableCell className="text-right tabular-nums text-muted-foreground">
                {formatMs(route.p95_latency_ms)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
