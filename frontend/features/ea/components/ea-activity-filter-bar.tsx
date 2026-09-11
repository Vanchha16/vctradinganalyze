"use client";

import { FilterBar, FilterField } from "@/components/shared/filter-bar";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { EaEventType } from "@/services/types";

import { EA_EVENT_LABELS } from "./ea-event-text";

export type EaModeFilter = "all" | "live" | "dry";

export interface EaActivityFilters {
  mode: EaModeFilter;
  eventType?: EaEventType;
}

const EVENT_TYPES = Object.keys(EA_EVENT_LABELS) as EaEventType[];

export function EaActivityFilterBar({
  filters,
  onChange,
}: {
  filters: EaActivityFilters;
  onChange: (next: Partial<EaActivityFilters>) => void;
}) {
  return (
    <FilterBar>
      <FilterField label="Mode">
        <Select value={filters.mode} onValueChange={(value) => onChange({ mode: value as EaModeFilter })}>
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Live and dry run</SelectItem>
            <SelectItem value="live">Live only</SelectItem>
            <SelectItem value="dry">Dry run only</SelectItem>
          </SelectContent>
        </Select>
      </FilterField>
      <FilterField label="Event">
        <Select
          value={filters.eventType ?? "all"}
          onValueChange={(value) => onChange({ eventType: value === "all" ? undefined : (value as EaEventType) })}
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All events</SelectItem>
            {EVENT_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {EA_EVENT_LABELS[type]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterField>
    </FilterBar>
  );
}
