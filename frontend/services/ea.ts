import { apiDelete, apiGet, apiPost } from "@/services/api-client";
import type { EaTokenCreatedResponse, EaTokenListResponse } from "@/services/types";

export function listEaTokens(): Promise<EaTokenListResponse> {
  return apiGet<EaTokenListResponse>("/ea/tokens");
}

export function createEaToken(name: string): Promise<EaTokenCreatedResponse> {
  return apiPost<EaTokenCreatedResponse>("/ea/tokens", { name });
}

export function revokeEaToken(id: string): Promise<void> {
  return apiDelete<void>(`/ea/tokens/${id}`);
}
