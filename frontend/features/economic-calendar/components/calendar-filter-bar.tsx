import { FilterBar, FilterField } from "@/components/shared/filter-bar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatEnumLabel } from "@/lib/format";
import type {
  EconomicEventCategory,
  EconomicEventImportance,
} from "@/services/types";

const IMPORTANCE_OPTIONS: EconomicEventImportance[] = [
  "critical",
  "high",
  "medium",
  "low",
];

const CATEGORY_OPTIONS: EconomicEventCategory[] = [
  "inflation",
  "employment",
  "growth",
  "central_bank",
  "consumer",
  "housing",
  "other",
];

/** The nine currencies the calendar providers cover (`finnhub`'s
 * country map and ForexFactory's `country` field agree on this set).
 * Hardcoded rather than derived from the current page's rows, which
 * would make the filter's options change as you filter. */
const CURRENCY_OPTIONS = [
  "USD",
  "EUR",
  "GBP",
  "JPY",
  "AUD",
  "CAD",
  "CHF",
  "CNY",
  "NZD",
];

const SORT_OPTIONS = [
  { value: "time_asc", label: "Soonest first" },
  { value: "time_desc", label: "Newest first" },
];

const RANGE_OPTIONS = [
  { value: "all", label: "All dates" },
  { value: "today", label: "Today" },
  { value: "week", label: "This week" },
];

export interface CalendarFilters {
  importance?: string;
  category?: string;
  range?: string;
  currency?: string;
  sort?: string;
  [key: string]: string | undefined;
}

export function CalendarFilterBar({
  filters,
  onChange,
}: {
  filters: CalendarFilters;
  onChange: (next: Partial<CalendarFilters>) => void;
}) {
  return (
    <FilterBar>
      <FilterField label="Range">
        <Select
          value={filters.range ?? "all"}
          onValueChange={(value) =>
            onChange({ range: value === "all" ? undefined : value })
          }
        >
          <SelectTrigger className="w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {RANGE_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterField>
      <FilterField label="Currency">
        <Select
          value={filters.currency ?? "all"}
          onValueChange={(value) =>
            onChange({ currency: value === "all" ? undefined : value })
          }
        >
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All currencies</SelectItem>
            {CURRENCY_OPTIONS.map((currency) => (
              <SelectItem key={currency} value={currency}>
                {currency}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterField>
      <FilterField label="Importance">
        <Select
          value={filters.importance ?? "all"}
          onValueChange={(value) =>
            onChange({ importance: value === "all" ? undefined : value })
          }
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All importance</SelectItem>
            {IMPORTANCE_OPTIONS.map((importance) => (
              <SelectItem key={importance} value={importance}>
                {formatEnumLabel(importance)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterField>
      <FilterField label="Category">
        <Select
          value={filters.category ?? "all"}
          onValueChange={(value) =>
            onChange({ category: value === "all" ? undefined : value })
          }
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {CATEGORY_OPTIONS.map((category) => (
              <SelectItem key={category} value={category}>
                {formatEnumLabel(category)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterField>
      <FilterField label="Sort">
        <Select
          value={filters.sort ?? "time_asc"}
          onValueChange={(value) =>
            onChange({ sort: value === "time_asc" ? undefined : value })
          }
        >
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {SORT_OPTIONS.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterField>
    </FilterBar>
  );
}
