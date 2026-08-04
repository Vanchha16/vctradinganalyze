"use client";

import { useQuery } from "@tanstack/react-query";

import { listCalendarEvents } from "@/services/calendar";
import type { EconomicEventCategory, EconomicEventImportance } from "@/services/types";

export function useCalendarEvents(params: {
  page?: number;
  limit?: number;
  country?: string;
  currency?: string;
  importance?: EconomicEventImportance;
  category?: EconomicEventCategory;
  range?: "today" | "week";
}) {
  return useQuery({
    queryKey: ["calendar-events", params],
    queryFn: () => listCalendarEvents(params),
  });
}
