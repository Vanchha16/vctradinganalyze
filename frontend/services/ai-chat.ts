import { apiDelete, apiGet, apiPost } from "@/services/api-client";
import type {
  ConversationDetailResponse,
  ConversationListResponse,
  ConversationResponse,
  ConversationStatus,
  CreateConversationRequest,
  SendMessageRequest,
  SendMessageResponse,
} from "@/services/types";

export function createConversation(payload: CreateConversationRequest): Promise<ConversationResponse> {
  return apiPost<ConversationResponse>("/chat/conversations", payload);
}

export function listConversations(params: {
  status?: ConversationStatus;
  page?: number;
  limit?: number;
}): Promise<ConversationListResponse> {
  return apiGet<ConversationListResponse>("/chat/conversations", {
    status: params.status,
    page: params.page?.toString(),
    limit: (params.limit ?? 20).toString(),
  });
}

export function getConversation(id: string): Promise<ConversationDetailResponse> {
  return apiGet<ConversationDetailResponse>(`/chat/conversations/${id}`);
}

export function sendMessage(conversationId: string, payload: SendMessageRequest): Promise<SendMessageResponse> {
  return apiPost<SendMessageResponse>(`/chat/conversations/${conversationId}/messages`, payload);
}

export function archiveConversation(id: string): Promise<ConversationResponse> {
  return apiPost<ConversationResponse>(`/chat/conversations/${id}/archive`);
}

export function deleteConversation(id: string): Promise<void> {
  return apiDelete(`/chat/conversations/${id}`);
}
