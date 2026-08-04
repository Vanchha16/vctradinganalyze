"use client";

import { Calendar } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { CalendarCardList } from "@/features/economic-calendar/components/calendar-card-list";
import { CalendarFilterBar, type CalendarFilters } from "@/features/economic-calendar/components/calendar-filter-bar";
import { CalendarTable } from "@/features/economic-calendar/components/calendar-table";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useCalendarEvents } from "@/hooks/use-calendar-events";
import { useQueryFilters } from "@/hooks/use-query-filters";
import type { EconomicEventCategory, EconomicEventImportance } from "@/services/types";

const DEFAULT_FILTERS: CalendarFilters = { importance: undefined, category: undefined, range: undefined };

export default function EconomicCalendarPage() {
  const { filters, page, setFilters, setPage } = useQueryFilters(DEFAULT_FILTERS);

  const eventsQuery = useCalendarEvents({
    importance: filters.importance as EconomicEventImportance | undefined,
    category: filters.category as EconomicEventCategory | undefined,
    range: filters.range as "today" | "week" | undefined,
    page,
    limit: 25,
  });

  const total = eventsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 25));

  return (
    <div>
      <PageHeader title="Economic Calendar" description="Scheduled and released economic events." />
      <CalendarFilterBar filters={filters} onChange={(next) => setFilters(next)} />
      <PageContainer>
        {eventsQuery.isLoading ? (
          <Skeleton className="h-96 w-full" />
        ) : eventsQuery.isError ? (
          <ErrorCard error={eventsQuery.error} onRetry={() => eventsQuery.refetch()} />
        ) : eventsQuery.data && eventsQuery.data.items.length > 0 ? (
          <>
            <div className="hidden md:block">
              <CalendarTable events={eventsQuery.data.items} />
            </div>
            <div className="md:hidden">
              <CalendarCardList events={eventsQuery.data.items} />
            </div>
            <div className="pt-4">
              <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
            </div>
          </>
        ) : (
          <EmptyState icon={Calendar} title="No events found" description="Try a different filter or date range." />
        )}
      </PageContainer>
    </div>
  );
}
