"use client";

import { X } from "lucide-react";

import { FilterBar, FilterField } from "@/components/shared/filter-bar";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatEnumLabel } from "@/lib/format";

/** Known values (docs/59 §11's actual write call sites, `AuthenticationService`/
 * `AdminUserService`) - hardcoded the same way `UserFilterBar`'s `ROLE_OPTIONS`
 * is, since there's no `GET /admin/logs/actions` enumeration endpoint and none
 * is warranted for a fixed, small set. */
const ACTION_OPTIONS = [
  "login_success",
  "login_failed",
  "logout",
  "session_revoked",
  "admin_user_created",
  "admin_user_updated",
  "admin_user_disabled",
  "admin_user_activated",
  "admin_role_changed",
  "admin_password_reset",
  "admin_user_deleted",
];

const RESOURCE_OPTIONS = ["user", "user_session"];

export interface AuditLogFilters {
  user_id?: string;
  action?: string;
  resource?: string;
  from?: string;
  to?: string;
  [key: string]: string | undefined;
}

export function AuditLogFilterBar({
  filters,
  onChange,
  actorLabel,
}: {
  filters: AuditLogFilters;
  onChange: (next: Partial<AuditLogFilters>) => void;
  /** Set when a row's actor was clicked to filter down to just them
   * (`AuditLogTable`'s `onFilterByActor`) - shown as a removable badge
   * since typing a raw actor UUID isn't a reasonable filter UX. */
  actorLabel?: string | null;
}) {
  return (
    <FilterBar>
      {actorLabel ? (
        <FilterField label="Actor">
          <Badge variant="outline" className="flex h-9 items-center gap-1.5 px-3">
            {actorLabel}
            <button
              type="button"
              aria-label="Clear actor filter"
              onClick={() => onChange({ user_id: undefined })}
              className="focus-ring rounded"
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        </FilterField>
      ) : null}
      <FilterField label="Action">
        <Select
          value={filters.action ?? "all"}
          onValueChange={(value) => onChange({ action: value === "all" ? undefined : value })}
        >
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All actions</SelectItem>
            {ACTION_OPTIONS.map((action) => (
              <SelectItem key={action} value={action}>
                {formatEnumLabel(action)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterField>
      <FilterField label="Resource">
        <Select
          value={filters.resource ?? "all"}
          onValueChange={(value) => onChange({ resource: value === "all" ? undefined : value })}
        >
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All resources</SelectItem>
            {RESOURCE_OPTIONS.map((resource) => (
              <SelectItem key={resource} value={resource}>
                {formatEnumLabel(resource)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterField>
      <FilterField label="From">
        <Input
          type="date"
          value={filters.from?.slice(0, 10) ?? ""}
          onChange={(event) =>
            onChange({ from: event.target.value ? `${event.target.value}T00:00:00Z` : undefined })
          }
          className="w-40"
        />
      </FilterField>
      <FilterField label="To">
        <Input
          type="date"
          value={filters.to?.slice(0, 10) ?? ""}
          onChange={(event) =>
            onChange({ to: event.target.value ? `${event.target.value}T23:59:59Z` : undefined })
          }
          className="w-40"
        />
      </FilterField>
    </FilterBar>
  );
}
