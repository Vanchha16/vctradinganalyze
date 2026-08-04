import { apiGet } from "@/services/api-client";
import type {
  NewsArticleDetailResponse,
  NewsArticleListResponse,
  NewsCategory,
  NewsImportance,
} from "@/services/types";

export function listNews(params: {
  page?: number;
  limit?: number;
  importance?: NewsImportance;
  category?: NewsCategory;
}): Promise<NewsArticleListResponse> {
  return apiGet<NewsArticleListResponse>("/news", {
    page: params.page?.toString(),
    limit: (params.limit ?? 20).toString(),
    importance: params.importance,
    category: params.category,
  });
}

export function getNewsById(id: string): Promise<NewsArticleDetailResponse> {
  return apiGet<NewsArticleDetailResponse>(`/news/${id}`);
}
