import { apiDelete, apiGet, apiPost } from "@/services/api-client";
import type { TelegramLinkResponse, TelegramStatusResponse } from "@/services/types";

export function createTelegramLink(): Promise<TelegramLinkResponse> {
  return apiPost<TelegramLinkResponse>("/telegram/link");
}

export function getTelegramStatus(): Promise<TelegramStatusResponse> {
  return apiGet<TelegramStatusResponse>("/telegram/status");
}

export function deleteTelegramLink(): Promise<void> {
  return apiDelete<void>("/telegram/link");
}
