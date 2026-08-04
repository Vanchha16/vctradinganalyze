"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { UserResponse } from "@/services/types";

/**
 * Read-only account summary + logout (ADR-104) - `PUT /users/profile`/
 * `POST /users/avatar`/`DELETE /users/account` have zero backend
 * implementation, so no edit/avatar/delete-account actions are offered.
 */
export function AccountSection({ user }: { user: UserResponse }) {
  const { logout } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    try {
      await logout();
    } catch (error) {
      if (error instanceof ApiError) toast.error(error.message);
    } finally {
      router.replace("/login");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Account</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted-foreground">Email</dt>
            <dd className="font-medium">{user.email}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Username</dt>
            <dd className="font-medium">@{user.username}</dd>
          </div>
        </dl>
        <div className="border-t border-border pt-4">
          <Button variant="destructive" onClick={() => void handleLogout()}>
            Log out
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
