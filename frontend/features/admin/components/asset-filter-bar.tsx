"use client";

import { Search } from "lucide-react";

import { FilterBar, FilterField } from "@/components/shared/filter-bar";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatEnumLabel } from "@/lib/format";
import type { MarketType } from "@/services/types";

const MARKET_TYPE_OPTIONS: MarketType[] = ["forex", "metal", "crypto", "index"];

export interface AdminAssetFilters {
  search?: string;
  market_type?: string;
  is_active?: string;
  [key: string]: string | undefined;
}

/** Admin symbol-management filter bar (Phase 9F) - mirrors
 * `UserFilterBar`'s shape, not `features/markets/components/asset-filter-bar.tsx`
 * (the public Markets page's read-only equivalent). */
export function AdminAssetFilterBar({
  filters,
  onChange,
}: {
  filters: AdminAssetFilters;
  onChange: (next: Partial<AdminAssetFilters>) => void;
}) {
  return (
    <FilterBar>
      <FilterField label="Search">
        <div className="focus-within:shadow-glow flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 transition-all focus-within:border-primary/40 md:w-72">
          <Search className="size-3.5 text-muted-foreground" />
          <input
            value={filters.search ?? ""}
            onChange={(event) => onChange({ search: event.target.value || undefined })}
            placeholder="Symbol or name…"
            className="w-full bg-transparent text-xs outline-none placeholder:text-muted-foreground"
          />
        </div>
      </FilterField>
      <FilterField label="Market Type">
        <Select
          value={filters.market_type ?? "all"}
          onValueChange={(value) => onChange({ market_type: value === "all" ? undefined : value })}
        >
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All markets</SelectItem>
            {MARKET_TYPE_OPTIONS.map((type) => (
              <SelectItem key={type} value={type}>
                {formatEnumLabel(type)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterField>
      <FilterField label="Status">
        <Select
          value={filters.is_active ?? "all"}
          onValueChange={(value) => onChange({ is_active: value === "all" ? undefined : value })}
        >
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="true">Active</SelectItem>
            <SelectItem value="false">Inactive</SelectItem>
          </SelectContent>
        </Select>
      </FilterField>
    </FilterBar>
  );
}
