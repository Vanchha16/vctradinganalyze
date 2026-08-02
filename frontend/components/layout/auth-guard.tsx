"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/hooks/use-auth";

/**
 * Gates the `(protected)` route group (docs/53 §3, ADR-099). Renders
 * nothing but a full-screen loading state while the session is being
 * restored ("idle"/"loading") - eliminates the flash of protected
 * content before auth status resolves, and the flash of a redirect that
 * immediately reverses itself once restoration finishes. Redirects to
 * `/login` (preserving the attempted path as `?next=`) once resolved to
 * "unauthenticated".
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "unauthenticated") {
      const next = pathname ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${next}`);
    }
  }, [status, pathname, router]);

  if (status === "idle" || status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-muted-foreground border-t-primary" />
      </div>
    );
  }

  if (status === "unauthenticated") {
    return null;
  }

  return <>{children}</>;
}
