import Link from "next/link";

import { Button } from "@/components/ui/button";

/**
 * Informational stub only (ADR-100) - `POST /auth/forgot-password` does
 * not exist on the backend yet (blocked on email infrastructure). No
 * form, no fabricated submission.
 */
export function ForgotPasswordNotice() {
  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-muted-foreground">
        Password reset isn&apos;t available yet - this feature depends on email delivery
        infrastructure that hasn&apos;t been built. Check back soon.
      </p>
      <Button asChild variant="secondary">
        <Link href="/login">Back to sign in</Link>
      </Button>
    </div>
  );
}
