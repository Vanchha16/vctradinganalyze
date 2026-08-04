"use client";

import { useQuery } from "@tanstack/react-query";

import { getUpcomingEvents } from "@/services/calendar";

export function useUpcomingEvents() {
  return useQuery({
    queryKey: ["upcoming-events"],
    queryFn: () => getUpcomingEvents(),
  });
}
