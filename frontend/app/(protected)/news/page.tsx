"use client";

import { Newspaper } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/ui/pagination";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { NewsCard } from "@/features/news/components/news-card";
import { NewsFilterBar, type NewsFilters } from "@/features/news/components/news-filter-bar";
import { useNewsList } from "@/hooks/use-news-list";
import { useQueryFilters } from "@/hooks/use-query-filters";
import type { NewsCategory, NewsImportance } from "@/services/types";

const DEFAULT_FILTERS: NewsFilters = { importance: undefined, category: undefined };

export default function NewsPage() {
  const { filters, page, setFilters, setPage } = useQueryFilters(DEFAULT_FILTERS);

  const newsQuery = useNewsList({
    importance: filters.importance as NewsImportance | undefined,
    category: filters.category as NewsCategory | undefined,
    page,
    limit: 20,
  });

  const total = newsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div>
      <PageHeader title="News" description="Market-moving news, sentiment-scored on ingestion." />
      <NewsFilterBar filters={filters} onChange={(next) => setFilters(next)} />
      <PageContainer>
        {newsQuery.isLoading ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-40 w-full" />
            ))}
          </div>
        ) : newsQuery.isError ? (
          <ErrorCard error={newsQuery.error} onRetry={() => newsQuery.refetch()} />
        ) : newsQuery.data && newsQuery.data.items.length > 0 ? (
          <>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {newsQuery.data.items.map((article) => (
                <NewsCard key={article.id} article={article} />
              ))}
            </div>
            <div className="pt-4">
              <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
            </div>
          </>
        ) : (
          <EmptyState icon={Newspaper} title="No news found" description="Try a different filter." />
        )}
      </PageContainer>
    </div>
  );
}
