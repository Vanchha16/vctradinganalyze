"use client";

import { useState } from "react";

import { Landmark } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader } from "@/components/shared/premium";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { AdminOrderTable } from "@/features/admin/components/admin-order-table";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAdminOrders } from "@/hooks/use-admin-orders";

const PAGE_SIZE = 20;

/**
 * `GET /admin/orders` (EA Bot spec §3F) - every real order the bot has
 * ever placed on the operator's live Exness account, view-only (no
 * manual close/modify from the dashboard this phase, per the spec's
 * out-of-scope list). Empty by default and expected to stay that way
 * until the operator personally reviews §12's dry-run output and sets
 * `EXECUTION_ENABLED=true` - the empty state below says so explicitly
 * rather than reading as a bug.
 */
export default function AdminOrdersPage() {
  const [page, setPage] = useState(1);
  const ordersQuery = useAdminOrders({ page, limit: PAGE_SIZE });

  const total = ordersQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = ordersQuery.data?.items ?? [];

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="Broker Orders"
          description="Every real order the EA Bot has placed on the connected Exness account."
        />

        <Panel>
          <PanelHeader
            title="All orders"
            subtitle={`${total} order${total === 1 ? "" : "s"}`}
            icon={<Landmark className="size-4" />}
          />
          {ordersQuery.isLoading ? (
            <div className="p-4">
              <Skeleton className="h-96 w-full" />
            </div>
          ) : ordersQuery.isError ? (
            <ErrorCard error={ordersQuery.error} onRetry={() => ordersQuery.refetch()} />
          ) : items.length > 0 ? (
            <>
              <AdminOrderTable orders={items} />
              <div className="px-5 pb-4">
                <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
              </div>
            </>
          ) : (
            <EmptyState
              icon={Landmark}
              title="No orders yet"
              description="Real orders only appear here once EXECUTION_ENABLED is turned on and a signal is actually executed. Until then, the bot only logs dry-run orders."
            />
          )}
        </Panel>
      </PageContainer>
    </div>
  );
}
