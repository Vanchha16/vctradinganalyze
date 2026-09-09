import { apiGet } from "@/services/api-client";
import type {
  EconomicEventCategory,
  EconomicEventImportance,
  EconomicEventListResponse,
  EconomicEventUpcomingResponse,
} from "@/services/types";

/** Only `release_time` is sortable server-side (ADR-151) - it is the
 * one column a calendar is ordered by and the only indexed one. */
export type CalendarSort = "time_asc" | "time_desc";

export function listCalendarEvents(params: {
  page?: number;
  limit?: number;
  country?: string;
  currency?: string;
  importance?: EconomicEventImportance;
  category?: EconomicEventCategory;
  range?: "today" | "week";
  sort?: CalendarSort;
}): Promise<EconomicEventListResponse> {
  return apiGet<EconomicEventListResponse>("/calendar", {
    page: params.page?.toString(),
    limit: (params.limit ?? 20).toString(),
    country: params.country,
    currency: params.currency,
    importance: params.importance,
    category: params.category,
    range: params.range,
    sort: params.sort,
  });
}

export function getUpcomingEvents(): Promise<EconomicEventUpcomingResponse> {
  return apiGet<EconomicEventUpcomingResponse>("/calendar/upcoming");
}
