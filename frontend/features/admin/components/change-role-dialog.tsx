"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useChangeAdminUserRole } from "@/hooks/use-admin-user-actions";
import { formatEnumLabel } from "@/lib/format";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { AdminUserResponse, UserRole } from "@/services/types";

const ALL_ROLES: UserRole[] = [
  "guest",
  "registered",
  "premium",
  "moderator",
  "support",
  "admin",
  "super_admin",
];

/** `PATCH /admin/users/{id}/role` is `require_super_admin`-only on the
 * backend (docs/59 §6.2) - this dialog is only ever rendered for a Super
 * Admin actor (`user-table.tsx` hides the "Change Role" action otherwise). */
export function ChangeRoleDialog({
  user,
  open,
  onOpenChange,
}: {
  user: AdminUserResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const changeRole = useChangeAdminUserRole();
  const [role, setRole] = useState<UserRole>(user?.role ?? "registered");

  function handleOpenChange(next: boolean) {
    if (next && user) setRole(user.role);
    onOpenChange(next);
  }

  async function handleSubmit() {
    if (!user) return;
    try {
      await changeRole.mutateAsync({ id: user.id, payload: { role } });
      toast.success(`${user.username}'s role changed to ${formatEnumLabel(role)}.`);
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to change role.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change role</DialogTitle>
          <DialogDescription>
            Change {user?.username}&rsquo;s role. This affects what they can access immediately.
          </DialogDescription>
        </DialogHeader>
        <Select value={role} onValueChange={(value) => setRole(value as UserRole)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ALL_ROLES.map((r) => (
              <SelectItem key={r} value={r}>
                {formatEnumLabel(r)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => void handleSubmit()}
            disabled={changeRole.isPending || role === user?.role}
          >
            {changeRole.isPending ? "Saving..." : "Change role"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
