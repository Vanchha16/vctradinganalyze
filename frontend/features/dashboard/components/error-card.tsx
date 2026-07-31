import { ApiError } from "@/services/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function ErrorCard({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const message = error instanceof ApiError ? error.message : "Something went wrong.";
  const hint =
    error instanceof ApiError && error.errorCode === "resource_not_found"
      ? "This asset likely has no candle data yet for the selected timeframe."
      : null;

  return (
    <Card className="border-destructive/50">
      <CardContent className="flex flex-col gap-3 pt-4">
        <p className="text-sm font-medium text-destructive">{message}</p>
        {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
        <Button size="sm" variant="secondary" className="w-fit" onClick={onRetry}>
          Retry
        </Button>
      </CardContent>
    </Card>
  );
}
