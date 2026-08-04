"use client";

import { Newspaper } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { WidgetSkeleton } from "@/components/shared/skeletons";
import { WidgetCard } from "@/features/dashboard/components/widget-card";
import { useNewsList } from "@/hooks/use-news-list";
import { importanceVariant } from "@/lib/badge-variants";
import { formatRelativeTime } from "@/lib/format";

export function BreakingNewsWidget() {
  const newsQuery = useNewsList({ importance: "high", limit: 5 });

  return (
    <WidgetCard title="Breaking News" viewAllHref="/news" icon={<Newspaper className="size-4" />}>
      {newsQuery.isLoading ? (
        <WidgetSkeleton />
      ) : newsQuery.data && newsQuery.data.items.length > 0 ? (
        <ul className="flex flex-col gap-2">
          {newsQuery.data.items.map((article) => (
            <li key={article.id}>
              <Link
                href={`/news/${article.id}`}
                className="focus-ring block rounded-md px-2 py-1.5 transition-colors hover:bg-surface/60"
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-medium leading-snug">{article.title}</p>
                  <Badge variant={importanceVariant(article.importance)} className="shrink-0">
                    {article.importance}
                  </Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{formatRelativeTime(article.published_at)}</p>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">No breaking news right now.</p>
      )}
    </WidgetCard>
  );
}
