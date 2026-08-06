import { apiDelete, apiGet, apiPatch, apiPost } from "@/services/api-client";
import type {
  AdminAnalyticsResponse,
  AdminAuditLogListResponse,
  AdminPasswordResetResponse,
  AdminSystemStatusResponse,
  AdminUserCreateRequest,
  AdminUserCreateResponse,
  AdminUserDetailResponse,
  AdminUserListResponse,
  AdminUserResponse,
  AdminUserRoleUpdateRequest,
  AdminUserStatusUpdateRequest,
  AdminUserUpdateRequest,
  MaintenanceAction,
  MaintenanceActionResponse,
  NewsRefreshResponse,
  SignalListResponse,
  SignalStatus,
} from "@/services/types";

/**
 * Thin wrappers over `/admin/users*`, `/admin/logs`, `/admin/signals`,
 * `/admin/system`, `/admin/analytics`, `/admin/news`, `/admin/maintenance`
 * (docs/59 §6.2/§11, docs/58 §3.2, Phase 7D-C, ADR-129/ADR-130) - mirrors
 * every other service module's shape (`services/signals.ts`), no business
 * logic here.
 */

export interface ListAdminUsersParams {
  search?: string;
  role?: string;
  is_active?: string;
  include_deleted?: string;
  page?: number;
  limit?: number;
}

export function listAdminUsers(params: ListAdminUsersParams): Promise<AdminUserListResponse> {
  return apiGet<AdminUserListResponse>("/admin/users", {
    search: params.search,
    role: params.role,
    is_active: params.is_active,
    include_deleted: params.include_deleted,
    page: params.page ? String(params.page) : undefined,
    limit: params.limit ? String(params.limit) : undefined,
  });
}

export function createAdminUser(payload: AdminUserCreateRequest): Promise<AdminUserCreateResponse> {
  return apiPost<AdminUserCreateResponse>("/admin/users", payload);
}

export function getAdminUser(id: string): Promise<AdminUserDetailResponse> {
  return apiGet<AdminUserDetailResponse>(`/admin/users/${id}`);
}

export function updateAdminUser(
  id: string,
  payload: AdminUserUpdateRequest,
): Promise<AdminUserResponse> {
  return apiPatch<AdminUserResponse>(`/admin/users/${id}`, payload);
}

export function deleteAdminUser(id: string): Promise<void> {
  return apiDelete<void>(`/admin/users/${id}`);
}

export function resetAdminUserPassword(id: string): Promise<AdminPasswordResetResponse> {
  return apiPost<AdminPasswordResetResponse>(`/admin/users/${id}/reset-password`);
}

export function setAdminUserStatus(
  id: string,
  payload: AdminUserStatusUpdateRequest,
): Promise<AdminUserResponse> {
  return apiPatch<AdminUserResponse>(`/admin/users/${id}/status`, payload);
}

export function changeAdminUserRole(
  id: string,
  payload: AdminUserRoleUpdateRequest,
): Promise<AdminUserResponse> {
  return apiPatch<AdminUserResponse>(`/admin/users/${id}/role`, payload);
}

export interface ListAdminLogsParams {
  user_id?: string;
  action?: string;
  resource?: string;
  from?: string;
  to?: string;
  page?: number;
  limit?: number;
}

export function listAdminLogs(params: ListAdminLogsParams): Promise<AdminAuditLogListResponse> {
  return apiGet<AdminAuditLogListResponse>("/admin/logs", {
    user_id: params.user_id,
    action: params.action,
    resource: params.resource,
    from: params.from,
    to: params.to,
    page: params.page ? String(params.page) : undefined,
    limit: params.limit ? String(params.limit) : undefined,
  });
}

export interface ListAdminSignalsParams {
  symbol?: string;
  status?: SignalStatus;
  page?: number;
  limit?: number;
}

export function listAdminSignals(params: ListAdminSignalsParams): Promise<SignalListResponse> {
  return apiGet<SignalListResponse>("/admin/signals", {
    symbol: params.symbol,
    status: params.status,
    page: params.page ? String(params.page) : undefined,
    limit: params.limit ? String(params.limit) : undefined,
  });
}

export function getAdminSystemStatus(): Promise<AdminSystemStatusResponse> {
  return apiGet<AdminSystemStatusResponse>("/admin/system");
}

export function getAdminAnalytics(): Promise<AdminAnalyticsResponse> {
  return apiGet<AdminAnalyticsResponse>("/admin/analytics");
}

/**
 * `signal` (`AbortSignal`) lets the two maintenance-action mutation hooks
 * enforce a client-side timeout - the backend runs ingestion synchronously
 * (ADR-130), so a slow/hung request must not leave a button disabled
 * forever with no way out.
 */
export function refreshNews(signal?: AbortSignal): Promise<NewsRefreshResponse> {
  return apiPost<NewsRefreshResponse>("/admin/news", undefined, undefined, signal);
}

export function runAdminMaintenance(
  action: MaintenanceAction,
  signal?: AbortSignal,
): Promise<MaintenanceActionResponse> {
  return apiPost<MaintenanceActionResponse>("/admin/maintenance", { action }, undefined, signal);
}
