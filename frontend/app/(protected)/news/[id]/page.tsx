"use client";

import { Sparkles } from "lucide-react";
import { useParams, useRouter } from "next/navigation";

import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useGenerateAiAnalysis } from "@/hooks/use-generate-ai-analysis";
import { useNewsArticle } from "@/hooks/use-news-article";
import { importanceVariant, newsSentimentVariant } from "@/lib/badge-variants";
import { formatDateTime, formatEnumLabel } from "@/lib/format";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";

//: Reuses the exact same AI Analysis pipeline the Markets/AI Analysis
//: pages already trigger (POST /analysis/ai/{symbol}) - this button is
//: only a shortcut entry point scoped to this article's affected assets,
//: not a separate news-only analysis path.
const ANALYSIS_TIMEFRAME = "h1";

export default function NewsDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const articleQuery = useNewsArticle(params.id);
  const generate = useGenerateAiAnalysis();

  async function handleAnalyze(symbol: string) {
    try {
      const result = await generate.mutateAsync({ symbol, timeframe: ANALYSIS_TIMEFRAME });
      router.push(`/ai-analysis/${result.id}`);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error(message);
    }
  }

  if (articleQuery.isLoading) {
    return (
      <PageContainer>
        <Skeleton className="h-64 w-full" />
      </PageContainer>
    );
  }

  if (articleQuery.isError || !articleQuery.data) {
    return (
      <PageContainer>
        <ErrorCard error={articleQuery.error} onRetry={() => articleQuery.refetch()} />
      </PageContainer>
    );
  }

  const article = articleQuery.data;

  return (
    <div>
      <PageHeader title={article.title} description={`${article.source} · ${formatDateTime(article.published_at)}`} />
      <PageContainer>
        <div className="flex flex-col gap-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={importanceVariant(article.importance)}>{formatEnumLabel(article.importance)}</Badge>
            <Badge variant="outline">{formatEnumLabel(article.category)}</Badge>
            {article.sentiment ? (
              <Badge variant={newsSentimentVariant(article.sentiment.sentiment)}>
                {formatEnumLabel(article.sentiment.sentiment)}
              </Badge>
            ) : null}
          </div>

          <Card>
            <CardContent className="pt-4 text-sm leading-relaxed">
              {article.content ?? article.summary ?? "No content available."}
            </CardContent>
          </Card>

          {article.sentiment ? (
            <Card>
              <CardContent className="flex flex-col gap-3 pt-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Sentiment Analysis
                </p>
                <p className="text-sm">{article.sentiment.reason}</p>
                {article.sentiment.ai_summary ? (
                  <p className="text-sm text-muted-foreground">{article.sentiment.ai_summary}</p>
                ) : null}
                {article.sentiment.affected_assets.length > 0 ? (
                  <div className="flex flex-col gap-3">
                    <div className="flex flex-wrap gap-2">
                      {article.sentiment.affected_assets.map((symbol) => (
                        <Badge key={symbol} variant="outline">
                          {symbol}
                        </Badge>
                      ))}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {article.sentiment.affected_assets.map((symbol) => (
                        <Button
                          key={symbol}
                          size="sm"
                          variant="secondary"
                          disabled={generate.isPending}
                          onClick={() => void handleAnalyze(symbol)}
                        >
                          <Sparkles className="size-3.5" />
                          {generate.isPending ? "Analyzing..." : `Should I buy or sell ${symbol}?`}
                        </Button>
                      ))}
                    </div>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ) : null}

          {article.url ? (
            <a
              href={article.url}
              target="_blank"
              rel="noreferrer"
              className="text-sm font-medium text-primary hover:underline"
            >
              Read original source →
            </a>
          ) : null}
        </div>
      </PageContainer>
    </div>
  );
}
