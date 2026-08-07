"use client";

import { ArrowDown, ArrowUp, ArrowUpDown, MoreVertical, Pencil, Power } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { assetActiveVariant } from "@/lib/badge-variants";
import { formatEnumLabel } from "@/lib/format";
import type { Asset } from "@/services/types";

export type AdminAssetSortKey = "symbol" | "name" | "market_type" | "is_active";

const COLUMNS: { key: AdminAssetSortKey; label: string }[] = [
  { key: "symbol", label: "Symbol" },
  { key: "name", label: "Name" },
  { key: "market_type", label: "Market" },
  { key: "is_active", label: "Status" },
];

function SortIcon({ active, order }: { active: boolean; order: "asc" | "desc" }) {
  if (!active) return <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground/70" />;
  return order === "asc" ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />;
}

interface AdminAssetTableProps {
  assets: Asset[];
  sort: AdminAssetSortKey;
  order: "asc" | "desc";
  onSortChange: (key: AdminAssetSortKey) => void;
  onEdit: (asset: Asset) => void;
  onToggleStatus: (asset: Asset) => void;
}

function RowActions({
  asset,
  onEdit,
  onToggleStatus,
}: {
  asset: Asset;
} & Pick<AdminAssetTableProps, "onEdit" | "onToggleStatus">) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="w-8 px-0" aria-label={`Actions for ${asset.symbol}`}>
          <MoreVertical className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => onEdit(asset)}>
          <Pencil className="mr-2 h-4 w-4" />
          Edit
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => onToggleStatus(asset)}>
          <Power className="mr-2 h-4 w-4" />
          {asset.is_active ? "Deactivate" : "Activate"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Admin symbol-management table (Phase 9F) - mirrors `UserTable`'s
 * shape. Distinct from `features/markets/components/asset-table.tsx`
 * (the public, read-only Markets table with Analyze/Signal quick
 * actions, no Edit/Activate/Deactivate). */
export function AdminAssetTable({
  assets,
  sort,
  order,
  onSortChange,
  onEdit,
  onToggleStatus,
}: AdminAssetTableProps) {
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
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {assets.map((asset) => (
          <TableRow key={asset.id}>
            <TableCell>
              <span className="text-[13px] font-semibold text-foreground">{asset.symbol}</span>
            </TableCell>
            <TableCell className="text-muted-foreground">{asset.name}</TableCell>
            <TableCell>
              <Badge variant="outline">{formatEnumLabel(asset.market_type)}</Badge>
            </TableCell>
            <TableCell>
              <Badge variant={assetActiveVariant(asset.is_active)}>
                {asset.is_active ? "Active" : "Inactive"}
              </Badge>
            </TableCell>
            <TableCell className="text-muted-foreground">{asset.exchange ?? "—"}</TableCell>
            <TableCell>
              <div className="flex justify-end">
                <RowActions asset={asset} onEdit={onEdit} onToggleStatus={onToggleStatus} />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
