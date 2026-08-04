"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { sendMessage } from "@/services/ai-chat";
import type { SendMessageRequest } from "@/services/types";

export function useSendMessage(conversationId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: SendMessageRequest) => sendMessage(conversationId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["conversation", conversationId] });
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}
