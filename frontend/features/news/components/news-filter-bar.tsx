import { FilterBar, FilterField } from "@/components/shared/filter-bar";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatEnumLabel } from "@/lib/format";
import type { NewsCategory, NewsImportance } from "@/services/types";

const IMPORTANCE_OPTIONS: NewsImportance[] = ["critical", "high", "medium", "low", "ignore"];

const CATEGORY_OPTIONS: NewsCategory[] = [
  "central_bank",
  "inflation",
  "employment",
  "gdp",
  "interest_rates",
  "politics",
  "war",
  "energy",
  "commodities",
  "crypto",
  "regulation",
  "corporate_earnings",
  "breaking_news",
];

export interface NewsFilters {
  importance?: string;
  category?: string;
  [key: string]: string | undefined;
}

export function NewsFilterBar({
  filters,
  onChange,
}: {
  filters: NewsFilters;
  onChange: (next: Partial<NewsFilters>) => void;
}) {
  return (
    <FilterBar>
      <FilterField label="Importance">
        <Select
          value={filters.importance ?? "all"}
          onValueChange={(value) => onChange({ importance: value === "all" ? undefined : value })}
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
          onValueChange={(value) => onChange({ category: value === "all" ? undefined : value })}
        >
          <SelectTrigger className="w-48">
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
    </FilterBar>
  );
}
