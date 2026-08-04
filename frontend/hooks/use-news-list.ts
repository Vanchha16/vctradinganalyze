"use client";

import { useQuery } from "@tanstack/react-query";

import { listNews } from "@/services/news";
import type { NewsCategory, NewsImportance } from "@/services/types";

export function useNewsList(params: {
  page?: number;
  limit?: number;
  importance?: NewsImportance;
  category?: NewsCategory;
}) {
  return useQuery({
    queryKey: ["news", params],
    queryFn: () => listNews(params),
  });
}
