"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createConversation } from "@/services/ai-chat";
import type { CreateConversationRequest } from "@/services/types";

export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateConversationRequest) => createConversation(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}
