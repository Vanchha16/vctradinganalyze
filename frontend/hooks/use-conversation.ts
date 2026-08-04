"use client";

import { useQuery } from "@tanstack/react-query";

import { getConversation } from "@/services/ai-chat";

export function useConversation(id: string | null) {
  return useQuery({
    queryKey: ["conversation", id],
    queryFn: () => getConversation(id as string),
    enabled: Boolean(id),
  });
}
