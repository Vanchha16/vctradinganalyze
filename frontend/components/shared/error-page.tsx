import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

/**
 * Full-page 404/500 fallback (docs/53 §6) - distinct from `ErrorCard`
 * (features/dashboard/components/error-card.tsx), which stays for
 * widget-level API errors inside a page, not whole-page failures.
 */
export function ErrorPage({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-4 text-center">
      <p className="text-lg font-semibold">{title}</p>
      <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      {action ?? (
        <Button asChild variant="secondary">
          <Link href="/dashboard">Back to dashboard</Link>
        </Button>
      )}
    </div>
  );
}
