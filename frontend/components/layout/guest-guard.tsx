"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/hooks/use-auth";

/**
 * Gates the `(auth)` route group - the inverse of `AuthGuard`. An
 * already-authenticated user visiting `/login`/`/register` is redirected
 * straight to `/dashboard` (or `?next=` if one was preserved from a prior
 * protected-route redirect), rather than being shown a login form for a
 * session they already have.
 */
export function GuestGuard({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (status === "authenticated") {
      const next = searchParams.get("next");
      router.replace(next && next.startsWith("/") ? next : "/dashboard");
    }
  }, [status, searchParams, router]);

  if (status === "idle" || status === "loading" || status === "authenticated") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-primary" />
      </div>
    );
  }

  return <>{children}</>;
}
