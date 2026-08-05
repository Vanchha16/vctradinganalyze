"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/hooks/use-auth";

const ADMIN_ROLES = new Set(["admin", "super_admin"]);

/**
 * Gates the `/admin/*` route group (docs/59 §5.1). Client-side only, same
 * layering as every other route guard since ADR-099 - this is a UX
 * convenience, not the security boundary. The real boundary is
 * `require_admin`/`require_super_admin` on the backend; a non-admin who
 * somehow reaches an admin page's UI gets real `403`s from every API call.
 *
 * Runs *inside* `AuthGuard` (the `(protected)` layout already handles the
 * unauthenticated case) - only adds the role check on top.
 */
export function AdminGuard({ children }: { children: React.ReactNode }) {
  const { user, status } = useAuth();
  const router = useRouter();

  const isAdmin = user ? ADMIN_ROLES.has(user.role) : false;

  useEffect(() => {
    if (status === "authenticated" && !isAdmin) {
      router.replace("/dashboard");
    }
  }, [status, isAdmin, router]);

  if (status !== "authenticated" || !isAdmin) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
