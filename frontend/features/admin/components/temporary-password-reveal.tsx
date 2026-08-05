"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { toast } from "@/lib/toast";

/**
 * Shown exactly once, per docs/59 §6.2/§11 - "never persisted in
 * plaintext, never logged" applies to the backend; on the frontend this
 * means never storing it in component state beyond this dialog's lifetime
 * and never sending it anywhere but the clipboard. Shared by
 * `AddUserDialog` and `ResetPasswordDialog` - the one genuinely duplicated
 * bit of UI between those two otherwise-distinct flows.
 */
export function TemporaryPasswordReveal({ password }: { password: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(password);
      setCopied(true);
      toast.success("Password copied to clipboard.");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Could not copy - select and copy manually.");
    }
  }

  return (
    <div className="rounded-lg border border-warning/30 bg-warning/10 p-4">
      <p className="text-xs font-medium text-warning">
        Temporary password - shown once, save it now
      </p>
      <div className="mt-2 flex items-center justify-between gap-2 rounded-md border border-border bg-surface px-3 py-2">
        <code className="select-all break-all text-sm font-medium tracking-wide">{password}</code>
        <button
          type="button"
          onClick={() => void handleCopy()}
          aria-label="Copy temporary password"
          className="focus-ring shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
        >
          {copied ? <Check className="size-4 text-success" /> : <Copy className="size-4" />}
        </button>
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground">
        This account must change its password on next login.
      </p>
    </div>
  );
}
