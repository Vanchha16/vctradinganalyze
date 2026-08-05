"use client";

import { Search } from "lucide-react";

import { FilterBar, FilterField } from "@/components/shared/filter-bar";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatEnumLabel } from "@/lib/format";
import type { UserRole } from "@/services/types";

const ROLE_OPTIONS: UserRole[] = [
  "guest",
  "registered",
  "premium",
  "moderator",
  "support",
  "admin",
  "super_admin",
];

export interface UserFilters {
  search?: string;
  role?: string;
  is_active?: string;
  include_deleted?: string;
  [key: string]: string | undefined;
}

export function UserFilterBar({
  filters,
  onChange,
  actorIsSuperAdmin,
}: {
  filters: UserFilters;
  onChange: (next: Partial<UserFilters>) => void;
  /** `include_deleted` is Super-Admin-only on the backend (docs/59 §6.2) -
   * the toggle is hidden for a plain Admin actor rather than shown and
   * always failing. */
  actorIsSuperAdmin: boolean;
}) {
  return (
    <FilterBar>
      <FilterField label="Search">
        <div className="focus-within:shadow-glow flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 transition-all focus-within:border-primary/40 md:w-72">
          <Search className="size-3.5 text-muted-foreground" />
          <input
            value={filters.search ?? ""}
            onChange={(event) => onChange({ search: event.target.value || undefined })}
            placeholder="Email, username, or name…"
            className="w-full bg-transparent text-xs outline-none placeholder:text-muted-foreground"
          />
        </div>
      </FilterField>
      <FilterField label="Role">
        <Select
          value={filters.role ?? "all"}
          onValueChange={(value) => onChange({ role: value === "all" ? undefined : value })}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All roles</SelectItem>
            {ROLE_OPTIONS.map((role) => (
              <SelectItem key={role} value={role}>
                {formatEnumLabel(role)}
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
            <SelectItem value="false">Disabled</SelectItem>
          </SelectContent>
        </Select>
      </FilterField>
      {actorIsSuperAdmin ? (
        <FilterField label="Deleted">
          <Select
            value={filters.include_deleted ?? "false"}
            onValueChange={(value) => onChange({ include_deleted: value === "true" ? "true" : undefined })}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="false">Exclude deleted</SelectItem>
              <SelectItem value="true">Include deleted</SelectItem>
            </SelectContent>
          </Select>
        </FilterField>
      ) : null}
    </FilterBar>
  );
}
