import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatDateTime, formatEnumLabel } from "@/lib/format";
import type { UserResponse } from "@/services/types";

/**
 * Read-only (ADR-104) - only `GET /auth/me` exists on the backend; no
 * edit form, no avatar upload.
 */
export function ProfileSummary({ user }: { user: UserResponse }) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-4 pt-4">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-lg font-semibold">
            {user.username.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <p className="text-base font-semibold">{user.full_name ?? user.username}</p>
            <p className="text-sm text-muted-foreground">@{user.username}</p>
          </div>
        </div>

        <dl className="grid grid-cols-1 gap-5 border-t border-border pt-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted-foreground">Email</dt>
            <dd className="font-medium">{user.email}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Role</dt>
            <dd className="pt-0.5">
              <Badge variant="outline">{formatEnumLabel(user.role)}</Badge>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Account Status</dt>
            <dd className="pt-0.5">
              <Badge variant={user.is_active ? "success" : "secondary"}>
                {user.is_active ? "Active" : "Inactive"}
              </Badge>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Email Verified</dt>
            <dd className="pt-0.5">
              <Badge variant={user.is_verified ? "success" : "outline"}>
                {user.is_verified ? "Verified" : "Not verified"}
              </Badge>
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Last Login</dt>
            <dd className="font-medium">{formatDateTime(user.last_login)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Member Since</dt>
            <dd className="font-medium">{formatDateTime(user.created_at)}</dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}
