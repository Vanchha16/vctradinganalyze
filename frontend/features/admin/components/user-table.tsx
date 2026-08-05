"use client";

import { ArrowDown, ArrowUp, ArrowUpDown, Eye, KeyRound, MoreVertical, Pencil, Power, ShieldCheck, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { userRoleVariant, userStatusVariant } from "@/lib/badge-variants";
import { formatDateTime, formatEnumLabel } from "@/lib/format";
import type { AdminUserResponse, UserResponse } from "@/services/types";

export type UserSortKey = "username" | "role" | "is_active" | "last_login" | "created_at";

const COLUMNS: { key: UserSortKey; label: string }[] = [
  { key: "username", label: "User" },
  { key: "role", label: "Role" },
  { key: "is_active", label: "Status" },
  { key: "last_login", label: "Last Login" },
  { key: "created_at", label: "Created At" },
];

const ADMIN_TIER = new Set(["admin", "super_admin"]);

function SortIcon({ active, order }: { active: boolean; order: "asc" | "desc" }) {
  if (!active) return <ArrowUpDown className="h-3.5 w-3.5 text-muted-foreground/70" />;
  return order === "asc" ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />;
}

interface UserTableProps {
  users: AdminUserResponse[];
  actor: UserResponse;
  sort: UserSortKey;
  order: "asc" | "desc";
  onSortChange: (key: UserSortKey) => void;
  onView: (user: AdminUserResponse) => void;
  onEdit: (user: AdminUserResponse) => void;
  onToggleStatus: (user: AdminUserResponse) => void;
  onResetPassword: (user: AdminUserResponse) => void;
  onDelete: (user: AdminUserResponse) => void;
  onChangeRole: (user: AdminUserResponse) => void;
  /** Built from the currently loaded page so "Created by" can resolve a
   * creator's username without a new backend lookup endpoint - falls back
   * to a truncated id if the creator isn't on the current page. */
  usersById: Map<string, AdminUserResponse>;
}

function canActOn(actor: UserResponse, target: AdminUserResponse): boolean {
  // Mirrors AdminUserService._assert_can_act_on (docs/59 §11, ADR-121) -
  // hides actions the backend would reject anyway, not a security boundary.
  if (ADMIN_TIER.has(target.role) && actor.role !== "super_admin") return false;
  return true;
}

function RowActions({
  user,
  actor,
  onView,
  onEdit,
  onToggleStatus,
  onResetPassword,
  onDelete,
  onChangeRole,
}: {
  user: AdminUserResponse;
  actor: UserResponse;
} & Pick<
  UserTableProps,
  "onView" | "onEdit" | "onToggleStatus" | "onResetPassword" | "onDelete" | "onChangeRole"
>) {
  const allowed = canActOn(actor, user);
  const isSelf = user.id === actor.id;
  const isSuperAdmin = actor.role === "super_admin";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="w-8 px-0" aria-label={`Actions for ${user.username}`}>
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
  );
}

function CreatedByCell({
  user,
  usersById,
}: {
  user: AdminUserResponse;
  usersById: Map<string, AdminUserResponse>;
}) {
  if (!user.created_by_admin_id) {
    return <span className="text-muted-foreground">System</span>;
  }
  const creator = usersById.get(user.created_by_admin_id);
  return <span>{creator ? creator.username : user.created_by_admin_id.slice(0, 8)}</span>;
}

export function UserTable({
  users,
  actor,
  sort,
  order,
  onSortChange,
  onView,
  onEdit,
  onToggleStatus,
  onResetPassword,
  onDelete,
  onChangeRole,
  usersById,
}: UserTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {COLUMNS.map((column) => (
            <TableHead key={column.key}>
              <button
                type="button"
                onClick={() => onSortChange(column.key)}
                className="focus-ring flex items-center gap-1 rounded px-1.5 py-0.5 font-medium transition-colors hover:bg-surface-2 hover:text-foreground"
                aria-label={`Sort by ${column.label}`}
              >
                {column.label}
                <SortIcon active={sort === column.key} order={order} />
              </button>
            </TableHead>
          ))}
          <TableHead>Created By</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {users.map((user) => (
          <TableRow key={user.id}>
            <TableCell>
              <button
                type="button"
                onClick={() => onView(user)}
                className="focus-ring rounded text-left text-[13px] font-semibold text-foreground transition-colors hover:text-primary"
              >
                {user.full_name || user.username}
              </button>
              <p className="text-[11px] text-muted-foreground">{user.email}</p>
            </TableCell>
            <TableCell>
              <Badge variant={userRoleVariant(user.role)}>{formatEnumLabel(user.role)}</Badge>
            </TableCell>
            <TableCell>
              <div className="flex flex-wrap items-center gap-1.5">
                <Badge variant={userStatusVariant(user.is_active)}>
                  {user.is_active ? "Active" : "Disabled"}
                </Badge>
                {user.deleted_at ? <Badge variant="destructive">Deleted</Badge> : null}
              </div>
            </TableCell>
            <TableCell className="text-muted-foreground">{formatDateTime(user.last_login)}</TableCell>
            <TableCell className="text-muted-foreground">{formatDateTime(user.created_at)}</TableCell>
            <TableCell className="text-muted-foreground">
              <CreatedByCell user={user} usersById={usersById} />
            </TableCell>
            <TableCell>
              <div className="flex justify-end">
                <RowActions
                  user={user}
                  actor={actor}
                  onView={onView}
                  onEdit={onEdit}
                  onToggleStatus={onToggleStatus}
                  onResetPassword={onResetPassword}
                  onDelete={onDelete}
                  onChangeRole={onChangeRole}
                />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
