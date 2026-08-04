"use client";

import { Archive, ArrowUpRight, MoreVertical, Trash2 } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useArchiveConversation, useDeleteConversation } from "@/hooks/use-conversation-actions";
import { formatRelativeTime } from "@/lib/format";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { ConversationResponse } from "@/services/types";

export function ConversationList({ conversations }: { conversations: ConversationResponse[] }) {
  const archiveConversation = useArchiveConversation();
  const deleteConversation = useDeleteConversation();

  async function handleArchive(id: string) {
    try {
      await archiveConversation.mutateAsync(id);
      toast.success("Conversation archived.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Something went wrong.");
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteConversation.mutateAsync(id);
      toast.success("Conversation deleted.");
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Something went wrong.");
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {conversations.map((conversation) => (
        <Card key={conversation.id} interactive>
          <CardContent className="flex items-center justify-between gap-4 py-4">
            <Link href={`/ai-chat/${conversation.id}`} className="flex flex-1 flex-col gap-1">
              <p className="text-sm font-medium">{conversation.title ?? "New conversation"}</p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                {conversation.current_symbol ? (
                  <Badge variant="outline">{conversation.current_symbol}</Badge>
                ) : null}
                {conversation.status === "archived" ? <Badge variant="secondary">Archived</Badge> : null}
                <span>{formatRelativeTime(conversation.updated_at)}</span>
              </div>
            </Link>
            <div className="flex items-center gap-1">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-8 px-0"
                    aria-label="Conversation actions"
                    onClick={(event) => event.preventDefault()}
                  >
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {conversation.status !== "archived" ? (
                    <DropdownMenuItem onSelect={() => void handleArchive(conversation.id)}>
                      <Archive className="mr-2 h-4 w-4" />
                      Archive
                    </DropdownMenuItem>
                  ) : null}
                  <DropdownMenuItem
                    onSelect={() => void handleDelete(conversation.id)}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Link href={`/ai-chat/${conversation.id}`} aria-label="Open conversation">
                <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </Link>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
