import { apiGet } from "@/services/api-client";
import type {
  EconomicEventCategory,
  EconomicEventImportance,
  EconomicEventListResponse,
  EconomicEventResponse,
  EconomicEventUpcomingResponse,
} from "@/services/types";

export function listCalendarEvents(params: {
  page?: number;
  limit?: number;
  country?: string;
  currency?: string;
  importance?: EconomicEventImportance;
  category?: EconomicEventCategory;
  range?: "today" | "week";
}): Promise<EconomicEventListResponse> {
  return apiGet<EconomicEventListResponse>("/calendar", {
    page: params.page?.toString(),
    limit: (params.limit ?? 20).toString(),
    country: params.country,
    currency: params.currency,
    importance: params.importance,
    category: params.category,
    range: params.range,
  });
}

export function getCalendarEvent(id: string): Promise<EconomicEventResponse> {
  return apiGet<EconomicEventResponse>(`/calendar/${id}`);
}

export function getUpcomingEvents(): Promise<EconomicEventUpcomingResponse> {
  return apiGet<EconomicEventUpcomingResponse>("/calendar/upcoming");
}
