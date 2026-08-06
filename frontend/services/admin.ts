import { apiDelete, apiGet, apiPatch, apiPost } from "@/services/api-client";
import type {
  AdminAuditLogListResponse,
  AdminPasswordResetResponse,
  AdminUserCreateRequest,
  AdminUserCreateResponse,
  AdminUserDetailResponse,
  AdminUserListResponse,
  AdminUserResponse,
  AdminUserRoleUpdateRequest,
  AdminUserStatusUpdateRequest,
  AdminUserUpdateRequest,
} from "@/services/types";

/**
 * Thin wrappers over `/admin/users*` and `/admin/logs` (docs/59 §6.2/§11,
 * Phase 8C/8F) - mirrors every other service module's shape
 * (`services/signals.ts`), no business logic here.
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
