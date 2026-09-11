import { apiDelete, apiGet, apiPost } from "@/services/api-client";
import type {
  EaEventListResponse,
  EaEventType,
  EaTokenCreatedResponse,
  EaTokenListResponse,
} from "@/services/types";

export function listEaTokens(): Promise<EaTokenListResponse> {
  return apiGet<EaTokenListResponse>("/ea/tokens");
}

export function createEaToken(name: string): Promise<EaTokenCreatedResponse> {
  return apiPost<EaTokenCreatedResponse>("/ea/tokens", { name });
}

export function revokeEaToken(id: string): Promise<void> {
  return apiDelete<void>(`/ea/tokens/${id}`);
}

export interface ListEaEventsParams {
  signal_id?: string;
  dry_run?: boolean;
  event_type?: EaEventType;
  page?: number;
  limit?: number;
}

export function listEaEvents(params: ListEaEventsParams): Promise<EaEventListResponse> {
  return apiGet<EaEventListResponse>("/ea/events", {
    signal_id: params.signal_id,
    dry_run: params.dry_run === undefined ? undefined : String(params.dry_run),
    event_type: params.event_type,
    page: params.page === undefined ? undefined : String(params.page),
    limit: params.limit === undefined ? undefined : String(params.limit),
  });
}
