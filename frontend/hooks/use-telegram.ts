"use client";

import { useQuery } from "@tanstack/react-query";

import { getTelegramStatus } from "@/services/telegram";

export function useTelegramStatus() {
  return useQuery({
    queryKey: ["telegram-status"],
    queryFn: () => getTelegramStatus(),
  });
}
