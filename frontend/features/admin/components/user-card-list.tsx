"use client";

import { Eye, KeyRound, MoreVertical, Pencil, Power, ShieldCheck, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { userRoleVariant, userStatusVariant } from "@/lib/badge-variants";
import { formatDateTime, formatEnumLabel } from "@/lib/format";
import type { AdminUserResponse, UserResponse } from "@/services/types";

const ADMIN_TIER = new Set(["admin", "super_admin"]);

/** Mobile counterpart to `UserTable` - same data/callbacks, stacked-card
 * presentation, same pattern as `features/markets/components/asset-card-list.tsx`. */
export function UserCardList({
  users,
  actor,
  onView,
  onEdit,
  onToggleStatus,
  onResetPassword,
  onDelete,
  onChangeRole,
}: {
  users: AdminUserResponse[];
  actor: UserResponse;
  onView: (user: AdminUserResponse) => void;
  onEdit: (user: AdminUserResponse) => void;
  onToggleStatus: (user: AdminUserResponse) => void;
  onResetPassword: (user: AdminUserResponse) => void;
  onDelete: (user: AdminUserResponse) => void;
  onChangeRole: (user: AdminUserResponse) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      {users.map((user) => {
        const allowed = !ADMIN_TIER.has(user.role) || actor.role === "super_admin";
        const isSelf = user.id === actor.id;
        const isSuperAdmin = actor.role === "super_admin";

        return (
          <Card key={user.id}>
            <CardContent className="flex items-start justify-between gap-3 py-3">
              <button type="button" onClick={() => onView(user)} className="min-w-0 flex-1 text-left">
                <p className="truncate text-[13px] font-semibold text-foreground">
                  {user.full_name || user.username}
                </p>
                <p className="truncate text-[11px] text-muted-foreground">{user.email}</p>
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <Badge variant={userRoleVariant(user.role)}>{formatEnumLabel(user.role)}</Badge>
                  <Badge variant={userStatusVariant(user.is_active)}>
                    {user.is_active ? "Active" : "Disabled"}
                  </Badge>
                  {user.deleted_at ? <Badge variant="destructive">Deleted</Badge> : null}
                </div>
                <p className="mt-1.5 text-[10px] text-muted-foreground">
                  Last login {formatDateTime(user.last_login)}
                </p>
              </button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="w-8 shrink-0 px-0" aria-label={`Actions for ${user.username}`}>
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onSelect={() => onView(user)}>
                    <Eye className="mr-2 h-4 w-4" />
                    View
                  </DropdownMenuItem>
                  {allowed ? (
                    <DropdownMenuItem onSelect={() => onEdit(user)}>
                      <Pencil className="mr-2 h-4 w-4" />
                      Edit
                    </DropdownMenuItem>
                  ) : null}
                  {allowed ? (
                    <DropdownMenuItem onSelect={() => onToggleStatus(user)}>
                      <Power className="mr-2 h-4 w-4" />
                      {user.is_active ? "Disable" : "Enable"}
                    </DropdownMenuItem>
                  ) : null}
                  {allowed ? (
                    <DropdownMenuItem onSelect={() => onResetPassword(user)}>
                      <KeyRound className="mr-2 h-4 w-4" />
                      Reset Password
                    </DropdownMenuItem>
                  ) : null}
                  {isSuperAdmin ? (
                    <DropdownMenuItem onSelect={() => onChangeRole(user)}>
                      <ShieldCheck className="mr-2 h-4 w-4" />
                      Change Role
                    </DropdownMenuItem>
                  ) : null}
                  {allowed && !isSelf ? (
                    <>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onSelect={() => onDelete(user)}
                        className="text-destructive focus:text-destructive"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </>
                  ) : null}
                </DropdownMenuContent>
              </DropdownMenu>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
