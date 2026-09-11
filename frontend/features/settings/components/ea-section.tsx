"use client";

import { Check, Copy, KeyRound } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmActionDialog } from "@/features/admin/components/confirm-action-dialog";
import { useCreateEaToken, useEaTokens, useRevokeEaToken } from "@/hooks/use-ea-tokens";
import { formatDateTime } from "@/lib/format";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { EaTokenCreatedResponse, EaTokenResponse } from "@/services/types";

/**
 * Tokens for the MetaTrader 5 Expert Advisor (ADR-161). The EA runs in the
 * operator's own terminal and trades there; this page only issues the
 * credential it uses to read `GET /ea/signals`. Super admin only - the
 * backend enforces that, this component just doesn't render for anyone else.
 */
export function EaSection() {
  const { data, isLoading } = useEaTokens(true);
  const createToken = useCreateEaToken();
  const revokeToken = useRevokeEaToken();
  const [name, setName] = useState("");
  const [created, setCreated] = useState<EaTokenCreatedResponse | null>(null);
  const [revoking, setRevoking] = useState<EaTokenResponse | null>(null);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    try {
      const token = await createToken.mutateAsync(name.trim());
      setCreated(token);
      setName("");
    } catch (error) {
      if (error instanceof ApiError) toast.error(error.message);
    }
  }

  async function handleRevoke() {
    if (!revoking) return;
    try {
      await revokeToken.mutateAsync(revoking.id);
      if (created?.id === revoking.id) setCreated(null);
      toast.success(`Revoked "${revoking.name}". That EA will stop receiving signals.`);
      setRevoking(null);
    } catch (error) {
      if (error instanceof ApiError) toast.error(error.message);
    }
  }

  const tokens = data?.items ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>MT5 Expert Advisor</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm text-muted-foreground">
          Lets the Expert Advisor in your own MetaTrader 5 read signals and trade them there. This
          website never receives your broker login and never places orders itself.
        </p>

        {created ? <TokenReveal token={created.token} onDone={() => setCreated(null)} /> : null}

        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : tokens.length > 0 ? (
          <ul className="flex flex-col divide-y divide-border rounded-md border border-border">
            {tokens.map((token) => (
              <li
                key={token.id}
                className="flex flex-wrap items-center justify-between gap-3 px-3 py-2.5"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {token.name}{" "}
                    <span className="font-mono text-xs text-muted-foreground">
                      ••••{token.hint}
                    </span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Created {formatDateTime(token.created_at)} · Last used{" "}
                    {token.last_used_at ? formatDateTime(token.last_used_at) : "never"}
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => setRevoking(token)}>
                  Revoke
                </Button>
              </li>
            ))}
          </ul>
        ) : null}

        <form onSubmit={(event) => void handleCreate(event)} className="flex flex-wrap gap-2">
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Terminal name, e.g. Home PC"
            maxLength={64}
            className="min-w-0 flex-1 sm:max-w-xs"
            aria-label="Terminal name"
          />
          <Button type="submit" disabled={!name.trim() || createToken.isPending}>
            <KeyRound className="h-4 w-4" />
            Create token
          </Button>
        </form>
      </CardContent>

      <ConfirmActionDialog
        open={revoking !== null}
        onOpenChange={(open) => {
          if (!open) setRevoking(null);
        }}
        title="Revoke EA token?"
        description={`The EA using "${revoking?.name ?? ""}" will get an error on its next check and stop receiving signals. Orders it already placed stay in MT5.`}
        actionLabel="Revoke"
        variant="destructive"
        onConfirm={() => void handleRevoke()}
        isPending={revokeToken.isPending}
      />
    </Card>
  );
}

/** Shown once, straight after creation - the server keeps only a hash. */
function TokenReveal({ token, onDone }: { token: string; onDone: () => void }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(token);
      setCopied(true);
      toast.success("Token copied to clipboard.");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Could not copy - select and copy manually.");
    }
  }

  return (
    <div className="rounded-lg border border-warning/30 bg-warning/10 p-4">
      <p className="text-xs font-medium text-warning">New token - shown once, copy it now</p>
      <div className="mt-2 flex items-center justify-between gap-2 rounded-md border border-border bg-surface px-3 py-2">
        <code className="select-all break-all text-sm font-medium">{token}</code>
        <button
          type="button"
          onClick={() => void handleCopy()}
          aria-label="Copy EA token"
          className="focus-ring shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
        >
          {copied ? <Check className="size-4 text-success" /> : <Copy className="size-4" />}
        </button>
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground">
        Paste it into the EA&apos;s <span className="font-mono">EaToken</span> input. Anyone with
        it can read your signals, so treat it like a password.
      </p>
      <Button variant="ghost" size="sm" className="mt-2" onClick={onDone}>
        I&apos;ve saved it
      </Button>
    </div>
  );
}
