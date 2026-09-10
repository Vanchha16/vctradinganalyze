"use client";

import { Check, KeyRound, Loader2, Pencil, Trash2, X } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { formatDateTime } from "@/lib/format";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { ApiCredentialResponse } from "@/services/types";

/**
 * One editable API key (ADR-156).
 *
 * The input is `type="password"` and always starts empty - never
 * pre-filled, because the server cannot supply the current value and a
 * blank box that says "leave unchanged" is honest about that. The only
 * disclosure is `hint`, the last four characters.
 */
export function CredentialRow({
  credential,
  storageEnabled,
  onSave,
  onClear,
  isSaving,
}: {
  credential: ApiCredentialResponse;
  storageEnabled: boolean;
  onSave: (name: string, value: string) => Promise<unknown>;
  onClear: (name: string) => Promise<unknown>;
  isSaving: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");

  async function handleSave() {
    try {
      await onSave(credential.name, value.trim());
      // Cleared immediately on success so the key is not left sitting in
      // a DOM node for the rest of the session.
      setValue("");
      setEditing(false);
      toast.success(`${credential.description.split(" - ")[0]} key saved.`);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not save the key.");
    }
  }

  async function handleClear() {
    try {
      await onClear(credential.name);
      toast.success("Stored key removed - falling back to the server's .env value.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not clear the key.");
    }
  }

  return (
    <div className="flex flex-col gap-3 border-b border-border py-4 last:border-b-0">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <KeyRound className="size-4 text-muted-foreground" aria-hidden />
            <p className="font-medium">{LABELS[credential.name] ?? credential.name}</p>
            <SourceBadge credential={credential} />
          </div>
          <p className="pt-1 text-sm text-muted-foreground">{credential.description}</p>
          {credential.updated_at ? (
            <p className="pt-1 text-xs text-muted-foreground">
              Updated {formatDateTime(credential.updated_at)}
              {credential.updated_by ? ` by ${credential.updated_by}` : null}
            </p>
          ) : null}
        </div>

        {!editing ? (
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="secondary"
              disabled={!storageEnabled}
              onClick={() => setEditing(true)}
            >
              <Pencil className="size-3.5" />
              {credential.source === "database" ? "Replace" : "Set key"}
            </Button>
            {credential.source === "database" ? (
              <Button size="sm" variant="ghost" disabled={isSaving} onClick={() => void handleClear()}>
                <Trash2 className="size-3.5" />
                Clear
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>

      {editing ? (
        <div className="flex flex-wrap items-center gap-2">
          <Input
            type="password"
            autoComplete="off"
            spellCheck={false}
            placeholder="Paste the new key"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="max-w-md flex-1"
          />
          <Button size="sm" disabled={value.trim().length < 8 || isSaving} onClick={() => void handleSave()}>
            {isSaving ? <Loader2 className="size-3.5 animate-spin" /> : <Check className="size-3.5" />}
            Save
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setValue("");
              setEditing(false);
            }}
          >
            <X className="size-3.5" />
            Cancel
          </Button>
        </div>
      ) : null}
    </div>
  );
}

const LABELS: Record<string, string> = {
  twelve_data: "Twelve Data",
  news_api: "NewsAPI",
  openai: "OpenAI",
  telegram_bot: "Telegram Bot",
};

/**
 * "Stored" vs "From .env" is a real distinction, not decoration: a key
 * working fine from the environment would otherwise look identical to a
 * stored one, and Clear would appear to do nothing.
 */
function SourceBadge({ credential }: { credential: ApiCredentialResponse }) {
  if (credential.source === "database") {
    return (
      <Badge variant="success">
        Stored{credential.hint ? ` ••••${credential.hint}` : null}
      </Badge>
    );
  }
  if (credential.source === "environment") {
    return (
      <Badge variant="outline">
        From .env{credential.hint ? ` ••••${credential.hint}` : null}
      </Badge>
    );
  }
  return <Badge variant="destructive">Not set</Badge>;
}
