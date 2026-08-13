"use client";

import { useQuery } from "@tanstack/react-query";

import { type ListAdminOrdersParams, listAdminOrders } from "@/services/admin";

export function useAdminOrders(params: ListAdminOrdersParams) {
  return useQuery({
    queryKey: ["admin-orders", params],
    queryFn: () => listAdminOrders(params),
  });
}
