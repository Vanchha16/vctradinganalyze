import { FilterBar, FilterField } from "@/components/shared/filter-bar";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatEnumLabel } from "@/lib/format";
import type { SignalStatus } from "@/services/types";

const STATUS_OPTIONS: SignalStatus[] = [
  "active",
  "triggered",
  "expired",
  "cancelled",
  "closed",
  "successful",
  "stopped_out",
  "draft",
];

export interface SignalFilters {
  status?: string;
  symbol?: string;
  [key: string]: string | undefined;
}

/** `symbol` is a real server-side filter - `GET /signals` already accepts `?symbol=`. */
export function SignalFilterBar({
  filters,
  onChange,
}: {
  filters: SignalFilters;
  onChange: (next: Partial<SignalFilters>) => void;
}) {
  return (
    <FilterBar>
      <FilterField label="Symbol">
        <Input
          value={filters.symbol ?? ""}
          onChange={(event) => onChange({ symbol: event.target.value.toUpperCase() || undefined })}
          placeholder="e.g. EURUSD"
          className="w-32"
        />
      </FilterField>
      <FilterField label="Status">
        <Select
          value={filters.status ?? "all"}
          onValueChange={(value) => onChange({ status: value === "all" ? undefined : value })}
        >
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUS_OPTIONS.map((status) => (
              <SelectItem key={status} value={status}>
                {formatEnumLabel(status)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterField>
    </FilterBar>
  );
}
