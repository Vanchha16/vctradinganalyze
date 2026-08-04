"use client";

import { useQuery } from "@tanstack/react-query";

import { listConversations } from "@/services/ai-chat";
import type { ConversationStatus } from "@/services/types";

export function useConversations(params: { status?: ConversationStatus; page?: number; limit?: number }) {
  return useQuery({
    queryKey: ["conversations", params],
    queryFn: () => listConversations(params),
  });
}
