"use client";

import { Send } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCreateTelegramLink, useDeleteTelegramLink } from "@/hooks/use-telegram-actions";
import { useTelegramStatus } from "@/hooks/use-telegram";
import { formatDateTime } from "@/lib/format";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { TelegramLinkResponse } from "@/services/types";

/**
 * Connects `POST/GET/DELETE /telegram/link(/status)` (docs/57 §3) to the
 * Settings page - the backend has always supported linking, this is the
 * first UI for it. `signal_tasks.py`'s automatic hourly generation
 * broadcasts to every linked account (ADR-113), so linking here is what
 * makes those signals actually arrive in Telegram.
 */
export function TelegramSection() {
  const { data: status, isLoading } = useTelegramStatus();
  const createLink = useCreateTelegramLink();
  const deleteLink = useDeleteTelegramLink();
  const [pendingLink, setPendingLink] = useState<TelegramLinkResponse | null>(null);

  async function handleConnect() {
    try {
      const link = await createLink.mutateAsync();
      setPendingLink(link);
    } catch (error) {
      if (error instanceof ApiError) toast.error(error.message);
    }
  }

  async function handleUnlink() {
    try {
      await deleteLink.mutateAsync();
      setPendingLink(null);
      toast.success("Telegram disconnected.");
    } catch (error) {
      if (error instanceof ApiError) toast.error(error.message);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Telegram</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : status?.linked ? (
          <>
            <div className="flex items-center gap-2">
              <Badge variant="success">Connected</Badge>
              <span className="text-sm text-muted-foreground">
                Linked {formatDateTime(status.linked_at)}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              Trading signals are sent to your linked Telegram chat as they&apos;re generated.
            </p>
            <div>
              <Button
                variant="destructive"
                onClick={() => void handleUnlink()}
                disabled={deleteLink.isPending}
              >
                Disconnect
              </Button>
            </div>
          </>
        ) : pendingLink ? (
          <>
            <p className="text-sm text-muted-foreground">
              Open Telegram, message{" "}
              <span className="font-medium text-foreground">
                {pendingLink.bot_username.startsWith("@") ? "" : "@"}
                {pendingLink.bot_username}
              </span>
              , and send:
            </p>
            <code className="w-fit rounded-md bg-muted px-3 py-2 text-sm font-medium">
              /start {pendingLink.link_code}
            </code>
            <p className="text-xs text-muted-foreground">
              Code expires {formatDateTime(pendingLink.expires_at)}. Refresh this page after
              linking to confirm.
            </p>
          </>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              Connect Telegram to receive trading signals as they&apos;re generated.
            </p>
            <div>
              <Button onClick={() => void handleConnect()} disabled={createLink.isPending}>
                <Send className="h-4 w-4" />
                Connect Telegram
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
