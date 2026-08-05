"use client";

import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminUserDetail } from "@/hooks/use-admin-users";
import { userRoleVariant, userStatusVariant } from "@/lib/badge-variants";
import { formatDateTime, formatEnumLabel } from "@/lib/format";

/** `GET /admin/users/{id}` detail view (docs/59 §6.2). A `Sheet`-based
 * drawer, not a route - admins jump between many user records quickly
 * while the filtered list stays visible behind it (docs/59 §5.2). */
export function UserDetailDrawer({
  userId,
  onOpenChange,
}: {
  userId: string | null;
  onOpenChange: (open: boolean) => void;
}) {
  const detailQuery = useAdminUserDetail(userId);
  const user = detailQuery.data;

  return (
    <Sheet open={userId !== null} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-sm overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>User details</SheetTitle>
          <SheetDescription>Read-only account overview.</SheetDescription>
        </SheetHeader>

        {detailQuery.isLoading ? (
          <div className="mt-4 flex flex-col gap-3">
            <Skeleton className="h-6 w-2/3" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : user ? (
          <div className="mt-4 flex flex-col gap-4 text-sm">
            <div>
              <p className="text-base font-semibold">{user.full_name ?? user.username}</p>
              <p className="text-xs text-muted-foreground">@{user.username}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant={userRoleVariant(user.role)}>{formatEnumLabel(user.role)}</Badge>
              <Badge variant={userStatusVariant(user.is_active)}>
                {user.is_active ? "Active" : "Disabled"}
              </Badge>
              {user.must_change_password ? <Badge variant="outline">Must change password</Badge> : null}
              {user.deleted_at ? <Badge variant="destructive">Deleted</Badge> : null}
            </div>
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-xs">
              <dt className="text-muted-foreground">Email</dt>
              <dd className="text-right">{user.email}</dd>
              <dt className="text-muted-foreground">Active sessions</dt>
              <dd className="text-right">{user.active_session_count}</dd>
              <dt className="text-muted-foreground">Last login</dt>
              <dd className="text-right">{formatDateTime(user.last_login)}</dd>
              <dt className="text-muted-foreground">Created</dt>
              <dd className="text-right">{formatDateTime(user.created_at)}</dd>
              <dt className="text-muted-foreground">Created by</dt>
              <dd className="text-right">
                {user.created_by_admin_id ? user.created_by_admin_id.slice(0, 8) : "System"}
              </dd>
              {user.deleted_at ? (
                <>
                  <dt className="text-muted-foreground">Deleted</dt>
                  <dd className="text-right">{formatDateTime(user.deleted_at)}</dd>
                </>
              ) : null}
            </dl>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
