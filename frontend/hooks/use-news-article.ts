"use client";

import { useQuery } from "@tanstack/react-query";

import { getNewsById } from "@/services/news";

export function useNewsArticle(id: string | null) {
  return useQuery({
    queryKey: ["news-article", id],
    queryFn: () => getNewsById(id as string),
    enabled: Boolean(id),
  });
}
