"use client";

import { useMemo, useState } from "react";

import { UserPlus, Users as UsersIcon } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader, Tag } from "@/components/shared/premium";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { AddUserDialog } from "@/features/admin/components/add-user-dialog";
import { ChangeRoleDialog } from "@/features/admin/components/change-role-dialog";
import { ConfirmActionDialog } from "@/features/admin/components/confirm-action-dialog";
import { EditUserDialog } from "@/features/admin/components/edit-user-dialog";
import { ResetPasswordDialog } from "@/features/admin/components/reset-password-dialog";
import { UserCardList } from "@/features/admin/components/user-card-list";
import { UserDetailDrawer } from "@/features/admin/components/user-detail-drawer";
import { UserFilterBar, type UserFilters } from "@/features/admin/components/user-filter-bar";
import { UserTable, type UserSortKey } from "@/features/admin/components/user-table";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useSetAdminUserStatus, useDeleteAdminUser } from "@/hooks/use-admin-user-actions";
import { useAdminUsers } from "@/hooks/use-admin-users";
import { useAuth } from "@/hooks/use-auth";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { AdminUserResponse } from "@/services/types";

const DEFAULT_FILTERS: UserFilters = {
  search: undefined,
  role: undefined,
  is_active: undefined,
  include_deleted: undefined,
};

const PAGE_SIZE = 20;

/**
 * Production-quality admin Users page (Phase 8D). Server-side pagination
 * and search/role/status/include_deleted filters (all real `GET
 * /admin/users` query params, docs/59 §6.2) - only column *sorting* is
 * client-side, limited to the current page, since the backend has no
 * `sort` query param (same documented trade-off as Markets' `AssetTable`).
 */
export default function AdminUsersPage() {
  const { user: actor } = useAuth();
  const [filters, setFilters] = useState<UserFilters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<UserSortKey>("created_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");

  const [addOpen, setAddOpen] = useState(false);
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [editingUser, setEditingUser] = useState<AdminUserResponse | null>(null);
  const [statusTarget, setStatusTarget] = useState<AdminUserResponse | null>(null);
  const [resetTarget, setResetTarget] = useState<AdminUserResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminUserResponse | null>(null);
  const [roleTarget, setRoleTarget] = useState<AdminUserResponse | null>(null);

  const usersQuery = useAdminUsers({
    search: filters.search,
    role: filters.role,
    is_active: filters.is_active,
    include_deleted: filters.include_deleted,
    page,
    limit: PAGE_SIZE,
  });
  const setStatus = useSetAdminUserStatus();
  const deleteUser = useDeleteAdminUser();

  const actorIsSuperAdmin = actor?.role === "super_admin";
  const total = usersQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const items = useMemo(() => usersQuery.data?.items ?? [], [usersQuery.data]);

  const usersById = useMemo(() => new Map(items.map((u) => [u.id, u])), [items]);

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      const direction = order === "asc" ? 1 : -1;
      const aValue = a[sort as keyof AdminUserResponse];
      const bValue = b[sort as keyof AdminUserResponse];
      if (aValue === bValue) return 0;
      if (aValue === null) return 1;
      if (bValue === null) return -1;
      return aValue > bValue ? direction : -direction;
    });
  }, [items, sort, order]);

  function handleFilterChange(next: Partial<UserFilters>) {
    setFilters((prev) => ({ ...prev, ...next }));
    setPage(1);
  }

  function handleSortChange(key: UserSortKey) {
    if (key === sort) {
      setOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSort(key);
      setOrder("asc");
    }
  }

  async function handleToggleStatus() {
    if (!statusTarget) return;
    try {
      await setStatus.mutateAsync({
        id: statusTarget.id,
        payload: { is_active: !statusTarget.is_active },
      });
      toast.success(
        `${statusTarget.username} was ${statusTarget.is_active ? "disabled" : "enabled"}.`,
      );
      setStatusTarget(null);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to update status.");
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deleteUser.mutateAsync(deleteTarget.id);
      toast.success(`${deleteTarget.username} was deleted.`);
      setDeleteTarget(null);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to delete user.");
    }
  }

  if (!actor) return null;

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="Users"
          description="Search, filter, and manage every account on the platform."
          actions={
            <Button onClick={() => setAddOpen(true)}>
              <UserPlus className="mr-2 h-4 w-4" />
              Add user
            </Button>
          }
        />

        <UserFilterBar
          filters={filters}
          onChange={handleFilterChange}
          actorIsSuperAdmin={actorIsSuperAdmin}
        />

        <Panel>
          <PanelHeader
            title="All users"
            subtitle={`${total} account${total === 1 ? "" : "s"}`}
            icon={<UsersIcon className="size-4" />}
            right={<Tag tone="brand">Live</Tag>}
          />
          {usersQuery.isLoading ? (
            <div className="p-4">
              <Skeleton className="h-96 w-full" />
            </div>
          ) : usersQuery.isError ? (
            <ErrorCard error={usersQuery.error} onRetry={() => usersQuery.refetch()} />
          ) : sortedItems.length > 0 ? (
            <>
              <div className="hidden md:block">
                <UserTable
                  users={sortedItems}
                  actor={actor}
                  sort={sort}
                  order={order}
                  onSortChange={handleSortChange}
                  onView={(u) => setViewingId(u.id)}
                  onEdit={setEditingUser}
                  onToggleStatus={setStatusTarget}
                  onResetPassword={setResetTarget}
                  onDelete={setDeleteTarget}
                  onChangeRole={setRoleTarget}
                  usersById={usersById}
                />
              </div>
              <div className="p-3 md:hidden">
                <UserCardList
                  users={sortedItems}
                  actor={actor}
                  onView={(u) => setViewingId(u.id)}
                  onEdit={setEditingUser}
                  onToggleStatus={setStatusTarget}
                  onResetPassword={setResetTarget}
                  onDelete={setDeleteTarget}
                  onChangeRole={setRoleTarget}
                />
              </div>
              <div className="px-5 pb-4">
                <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
              </div>
            </>
          ) : (
            <EmptyState icon={UsersIcon} title="No users found" description="Try a different filter or search term." />
          )}
        </Panel>
      </PageContainer>

      <AddUserDialog open={addOpen} onOpenChange={setAddOpen} actorIsSuperAdmin={actorIsSuperAdmin} />
      <UserDetailDrawer userId={viewingId} onOpenChange={(open) => !open && setViewingId(null)} />
      <EditUserDialog
        user={editingUser}
        open={editingUser !== null}
        onOpenChange={(open) => !open && setEditingUser(null)}
      />
      <ChangeRoleDialog
        user={roleTarget}
        open={roleTarget !== null}
        onOpenChange={(open) => !open && setRoleTarget(null)}
      />
      <ResetPasswordDialog
        user={resetTarget}
        open={resetTarget !== null}
        onOpenChange={(open) => !open && setResetTarget(null)}
      />
      <ConfirmActionDialog
        open={statusTarget !== null}
        onOpenChange={(open) => !open && setStatusTarget(null)}
        title={statusTarget?.is_active ? "Disable user?" : "Enable user?"}
        description={
          statusTarget?.is_active
            ? `${statusTarget?.username} will be signed out of every session and unable to log in until re-enabled.`
            : `${statusTarget?.username} will be able to log in again.`
        }
        actionLabel={statusTarget?.is_active ? "Disable" : "Enable"}
        variant={statusTarget?.is_active ? "destructive" : "default"}
        onConfirm={() => void handleToggleStatus()}
        isPending={setStatus.isPending}
      />
      <ConfirmActionDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete user?"
        description={`${deleteTarget?.username} will be soft-deleted - hidden from listings and unable to log in. Their data is retained, not erased.`}
        actionLabel="Delete"
        variant="destructive"
        onConfirm={() => void handleDelete()}
        isPending={deleteUser.isPending}
      />
    </div>
  );
}
