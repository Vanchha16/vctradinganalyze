"use client";

import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { importanceVariant, newsSentimentVariant } from "@/lib/badge-variants";
import { formatEnumLabel, formatRelativeTime } from "@/lib/format";
import type { NewsArticleListItemResponse } from "@/services/types";

/**
 * Whole-card click target (docs/56 §10, Stage 5) - matches the
 * `Card interactive` + `router.push` pattern already used for AI
 * Analysis history rows and AI Chat conversation rows, replacing the
 * small icon-only affordance. Unlike `SignalCard`, this card has no
 * second independent action (no bookmark button), so the whole-card
 * click target has no ambiguity to resolve.
 */
export function NewsCard({ article }: { article: NewsArticleListItemResponse }) {
  const router = useRouter();

  return (
    <Card interactive onClick={() => router.push(`/news/${article.id}`)}>
      <CardHeader className="space-y-0 pb-2">
        <CardTitle className="text-sm leading-snug">{article.title}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {article.summary ? <p className="text-sm text-muted-foreground">{article.summary}</p> : null}
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={importanceVariant(article.importance)}>{formatEnumLabel(article.importance)}</Badge>
          {article.sentiment ? (
            <Badge variant={newsSentimentVariant(article.sentiment)}>{formatEnumLabel(article.sentiment)}</Badge>
          ) : null}
          <Badge variant="outline">{formatEnumLabel(article.category)}</Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          {article.source} · {formatRelativeTime(article.published_at)}
        </p>
      </CardContent>
    </Card>
  );
}
