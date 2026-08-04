"use client";

import { MessageCircle, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { FilterBar, FilterField } from "@/components/shared/filter-bar";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ListItemSkeleton } from "@/components/shared/skeletons";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { ConversationList } from "@/features/ai-chat/components/conversation-list";
import { useConversations } from "@/hooks/use-conversations";
import { useCreateConversation } from "@/hooks/use-create-conversation";
import { useQueryFilters } from "@/hooks/use-query-filters";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { ConversationStatus } from "@/services/types";

const DEFAULT_FILTERS = { status: "active", search: undefined };

export default function AiChatPage() {
  const router = useRouter();
  const { filters, setFilters } = useQueryFilters(DEFAULT_FILTERS);
  const status = (filters.status as ConversationStatus) ?? "active";

  const conversationsQuery = useConversations({ status, limit: 50 });
  const createConversation = useCreateConversation();

  const filteredConversations = useMemo(() => {
    const items = conversationsQuery.data?.items ?? [];
    const search = filters.search?.trim().toLowerCase();
    if (!search) return items;
    return items.filter((conversation) => (conversation.title ?? "New conversation").toLowerCase().includes(search));
  }, [conversationsQuery.data, filters.search]);

  async function handleNewConversation() {
    try {
      const conversation = await createConversation.mutateAsync({});
      router.push(`/ai-chat/${conversation.id}`);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error(message);
    }
  }

  return (
    <div>
      <PageHeader
        title="AI Chat"
        description="Ask about recommendations, signals, or trading concepts."
        actions={
          <Button onClick={() => void handleNewConversation()} disabled={createConversation.isPending}>
            <Plus className="mr-2 h-4 w-4" />
            New Conversation
          </Button>
        }
      />
      <FilterBar>
        <FilterField label="Search">
          <Input
            value={filters.search ?? ""}
            onChange={(event) => setFilters({ search: event.target.value || undefined })}
            placeholder="Search by title..."
            className="w-56"
          />
        </FilterField>
        <FilterField label="Status">
          <Select value={status} onValueChange={(value) => setFilters({ status: value })}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>
        </FilterField>
      </FilterBar>
      <PageContainer>
        {conversationsQuery.isLoading ? (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <ListItemSkeleton key={index} />
            ))}
          </div>
        ) : conversationsQuery.isError ? (
          <ErrorCard error={conversationsQuery.error} onRetry={() => conversationsQuery.refetch()} />
        ) : filteredConversations.length > 0 ? (
          <ConversationList conversations={filteredConversations} />
        ) : (
          <EmptyState
            icon={MessageCircle}
            title="No conversations yet"
            description="Start a new conversation to ask about any asset, signal, or trading concept."
            action={
              <Button onClick={() => void handleNewConversation()} variant="secondary">
                Start a conversation
              </Button>
            }
          />
        )}
      </PageContainer>
    </div>
  );
}
