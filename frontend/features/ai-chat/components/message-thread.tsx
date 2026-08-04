import Link from "next/link";

import { AiBadge } from "@/components/shared/ai-badge";
import { Markdown } from "@/components/shared/markdown-lazy";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/format";
import type { MessageResponse } from "@/services/types";

function TypingIndicator() {
  return (
    <span className="flex items-center gap-1 py-0.5" aria-label="Assistant is typing">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-current opacity-60"
          style={{ animationDelay: `${index * 120}ms` }}
        />
      ))}
    </span>
  );
}

/**
 * `pendingUserContent`/`showTypingIndicator` implement ADR-109's
 * "streaming-ready" optimistic UX: the chat page fills these in the
 * instant a message is submitted (before the request/response round
 * trip resolves), then clears them once the real `assistant_message`
 * arrives. A future SSE backend would only need to swap the static
 * typing indicator for progressively-appended text in a
 * `pendingAssistantContent` prop - this component's contract (a message
 * list plus one optional trailing pending pair) wouldn't change.
 */
export function MessageThread({
  messages,
  pendingUserContent,
  showTypingIndicator,
}: {
  messages: MessageResponse[];
  pendingUserContent?: string | null;
  showTypingIndicator?: boolean;
}) {
  return (
    <div className="flex flex-col gap-4">
      {messages.map((message) => {
        const isUser = message.role === "user";
        return (
          <div key={message.id} className={cn("flex flex-col gap-1", isUser ? "items-end" : "items-start")}>
            {isUser ? null : <AiBadge className="mb-0.5" />}
            <div
              className={cn(
                "max-w-[85%] rounded-xl px-4 py-2.5 text-sm shadow-sm",
                isUser
                  ? "whitespace-pre-wrap rounded-br-sm bg-primary text-primary-foreground"
                  : "rounded-bl-sm bg-secondary text-secondary-foreground",
              )}
            >
              {isUser ? message.content : <Markdown>{message.content}</Markdown>}
            </div>
            <div className="flex items-center gap-2 px-1 text-xs text-muted-foreground">
              <span>{formatDateTime(message.created_at)}</span>
              {message.ai_analysis_id ? (
                <Link href={`/ai-analysis/${message.ai_analysis_id}`} className="hover:text-foreground hover:underline">
                  View analysis
                </Link>
              ) : null}
              {message.signal_id ? (
                <Link href={`/signals/${message.signal_id}`} className="hover:text-foreground hover:underline">
                  View signal
                </Link>
              ) : null}
            </div>
          </div>
        );
      })}
      {pendingUserContent ? (
        <div className="flex flex-col items-end gap-1">
          <div className="max-w-[85%] whitespace-pre-wrap rounded-xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground opacity-70 shadow-sm">
            {pendingUserContent}
          </div>
        </div>
      ) : null}
      {showTypingIndicator ? (
        <div className="flex flex-col items-start gap-1">
          <AiBadge className="mb-0.5" />
          <div className="rounded-xl rounded-bl-sm bg-secondary px-4 py-2.5 text-secondary-foreground shadow-sm">
            <TypingIndicator />
          </div>
        </div>
      ) : null}
    </div>
  );
}
