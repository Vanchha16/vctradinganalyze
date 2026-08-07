"use client";

import { useQuery } from "@tanstack/react-query";

import { type ListAdminAssetsParams, listAdminAssets } from "@/services/admin";

export function useAdminAssets(params: ListAdminAssetsParams) {
  return useQuery({
    queryKey: ["admin-assets", params],
    queryFn: () => listAdminAssets(params),
  });
}
