"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { PageHeader } from "@/components/shared/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { MessageComposer } from "@/features/ai-chat/components/message-composer";
import { MessageThread } from "@/features/ai-chat/components/message-thread";
import { SuggestedPrompts } from "@/features/ai-chat/components/suggested-prompts";
import { useConversation } from "@/hooks/use-conversation";
import { useSendMessage } from "@/hooks/use-send-message";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { Timeframe } from "@/services/types";

export default function AiChatThreadPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const conversationQuery = useConversation(params.id);
  const sendMessage = useSendMessage(params.id);
  const [pendingUserContent, setPendingUserContent] = useState<string | null>(null);
  const [prefill, setPrefill] = useState<string | null>(null);

  async function handleSend(content: string, symbol?: string, timeframe?: Timeframe) {
    setPendingUserContent(content);
    try {
      await sendMessage.mutateAsync({ content, symbol, timeframe });
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error(message);
    } finally {
      setPendingUserContent(null);
    }
  }

  if (conversationQuery.isLoading) {
    return (
      <div className="p-6">
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (conversationQuery.isError || !conversationQuery.data) {
    return (
      <div className="p-6">
        <ErrorCard error={conversationQuery.error} onRetry={() => conversationQuery.refetch()} />
      </div>
    );
  }

  const conversation = conversationQuery.data;

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <PageHeader
        title={conversation.title ?? "New conversation"}
        description={conversation.current_symbol ? `Grounded to ${conversation.current_symbol}` : undefined}
        actions={
          <button
            type="button"
            onClick={() => router.push("/ai-chat")}
            className="text-sm text-muted-foreground hover:text-foreground hover:underline"
          >
            ← All conversations
          </button>
        }
      />
      <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
        {conversation.messages.length > 0 ? (
          <MessageThread
            messages={conversation.messages}
            pendingUserContent={pendingUserContent}
            showTypingIndicator={sendMessage.isPending}
          />
        ) : (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">
              Ask a question below - about a specific asset, a recommendation, or a general trading concept.
            </p>
            <SuggestedPrompts symbol={conversation.current_symbol} onSelect={setPrefill} />
          </div>
        )}
      </div>
      <MessageComposer
        onSend={(content, symbol, timeframe) => void handleSend(content, symbol, timeframe)}
        isSending={sendMessage.isPending}
        defaultSymbol={conversation.current_symbol}
        prefill={prefill}
      />
    </div>
  );
}
