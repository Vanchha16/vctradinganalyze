"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { createTelegramLink, deleteTelegramLink } from "@/services/telegram";

export function useCreateTelegramLink() {
  return useMutation({
    mutationFn: () => createTelegramLink(),
  });
}

export function useDeleteTelegramLink() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteTelegramLink(),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["telegram-status"] }),
  });
}
