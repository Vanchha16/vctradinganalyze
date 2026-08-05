"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  changeAdminUserRole,
  createAdminUser,
  deleteAdminUser,
  resetAdminUserPassword,
  setAdminUserStatus,
  updateAdminUser,
} from "@/services/admin";
import type {
  AdminUserCreateRequest,
  AdminUserRoleUpdateRequest,
  AdminUserStatusUpdateRequest,
  AdminUserUpdateRequest,
} from "@/services/types";

/** One mutation hook per admin action, all invalidating the same
 * `["admin-users"]` query key - mirrors `use-conversation-actions.ts`'s
 * shape (docs/59 Phase 8D). */

export function useCreateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: AdminUserCreateRequest) => createAdminUser(payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AdminUserUpdateRequest }) =>
      updateAdminUser(id, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useDeleteAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteAdminUser(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useResetAdminUserPassword() {
  return useMutation({
    mutationFn: (id: string) => resetAdminUserPassword(id),
  });
}

export function useSetAdminUserStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AdminUserStatusUpdateRequest }) =>
      setAdminUserStatus(id, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}

export function useChangeAdminUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AdminUserRoleUpdateRequest }) =>
      changeAdminUserRole(id, payload),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });
}
