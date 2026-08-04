import { ArrowDown, ArrowUp, ArrowUpDown, LineChart, Sparkles } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { assetActiveVariant } from "@/lib/badge-variants";
import { cn } from "@/lib/utils";
import { formatEnumLabel } from "@/lib/format";
import type { Asset } from "@/services/types";

export type AssetSortKey = "symbol" | "name" | "market_type" | "is_active";

const COLUMNS: { key: AssetSortKey; label: string }[] = [
  { key: "symbol", label: "Symbol" },
  { key: "name", label: "Name" },
  { key: "market_type", label: "Market" },
  { key: "is_active", label: "Status" },
];

function SortIcon({ active, order }: { active: boolean; order: "asc" | "desc" }) {
  if (!active) return <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground/70" />;
  return order === "asc" ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />;
}

export function AssetTable({
  assets,
  sort,
  order,
  onSortChange,
  selectedSymbol,
  onSelectSymbol,
}: {
  assets: Asset[];
  sort: AssetSortKey;
  order: "asc" | "desc";
  onSortChange: (key: AssetSortKey) => void;
  /** Optional: when provided, rows become selectable (desktop master-detail workspace) in addition to the Symbol link's normal navigation. */
  selectedSymbol?: string | null;
  onSelectSymbol?: (symbol: string) => void;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {COLUMNS.map((column) => (
            <TableHead key={column.key}>
              <button
                type="button"
                onClick={() => onSortChange(column.key)}
                className="focus-ring flex items-center gap-1 rounded px-1.5 py-0.5 font-medium transition-colors hover:bg-surface-2 hover:text-foreground"
                aria-label={`Sort by ${column.label}`}
              >
                {column.label}
                <SortIcon active={sort === column.key} order={order} />
              </button>
            </TableHead>
          ))}
          <TableHead>Exchange</TableHead>
          <TableHead className="text-right">Quick Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {assets.map((asset) => {
          const query = `?symbol=${asset.symbol}&timeframe=h1`;
          const selected = selectedSymbol === asset.symbol;
          return (
            <TableRow
              key={asset.id}
              onClick={onSelectSymbol ? () => onSelectSymbol(asset.symbol) : undefined}
              className={cn(onSelectSymbol && "cursor-pointer", selected && "bg-primary/8 hover:bg-primary/8")}
            >
              <TableCell>
                <Link href={`/markets/${asset.symbol}`} className="focus-ring rounded text-[13px] font-semibold text-foreground transition-colors hover:text-primary">
                  {asset.symbol}
                </Link>
              </TableCell>
              <TableCell className="w-full whitespace-normal text-[11px] text-muted-foreground">{asset.name}</TableCell>
              <TableCell>
                <Badge variant="outline">{formatEnumLabel(asset.market_type)}</Badge>
              </TableCell>
              <TableCell>
                <Badge variant={assetActiveVariant(asset.is_active)}>{asset.is_active ? "Active" : "Inactive"}</Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">{asset.exchange ?? "—"}</TableCell>
              <TableCell>
                <div className="flex items-center justify-end gap-1">
                  <Link
                    href={`/ai-analysis${query}`}
                    aria-label={`Analyze ${asset.symbol}`}
                    className="focus-ring rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
                  >
                    <Sparkles className="h-4 w-4" />
                  </Link>
                  <Link
                    href={`/signals${query}`}
                    aria-label={`Generate signal for ${asset.symbol}`}
                    className="focus-ring rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
                  >
                    <LineChart className="h-4 w-4" />
                  </Link>
                </div>
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
