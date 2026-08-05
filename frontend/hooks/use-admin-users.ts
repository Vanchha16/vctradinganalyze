"use client";

import { useQuery } from "@tanstack/react-query";

import { type ListAdminUsersParams, getAdminUser, listAdminUsers } from "@/services/admin";

export function useAdminUsers(params: ListAdminUsersParams) {
  return useQuery({
    queryKey: ["admin-users", params],
    queryFn: () => listAdminUsers(params),
  });
}

export function useAdminUserDetail(id: string | null) {
  return useQuery({
    queryKey: ["admin-users", "detail", id],
    queryFn: () => getAdminUser(id as string),
    enabled: id !== null,
  });
}
