import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceGauge } from "@/features/ai-analysis/components/confidence-gauge";
import { recommendationVariant, riskLevelVariant } from "@/lib/badge-variants";
import { formatEnumLabel, formatPrice } from "@/lib/format";
import type { AIAnalysisResponse } from "@/services/types";

/**
 * docs/05 §12's "Recommendation/Confidence/Risk Assessment" sections -
 * every field here is deterministic, reused verbatim from the backend
 * response (ADR-078/079) - this component only formats/displays.
 */
export function AnalysisSummary({ analysis }: { analysis: AIAnalysisResponse }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle>Summary</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <ConfidenceGauge score={analysis.confidence_score} level={analysis.confidence_level} />
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Badge variant={recommendationVariant(analysis.recommendation)} className="text-sm">
              {analysis.recommendation.toUpperCase()}
            </Badge>
            {analysis.risk_level ? (
              <Badge variant={riskLevelVariant(analysis.risk_level)}>{formatEnumLabel(analysis.risk_level)} risk</Badge>
            ) : null}
            {!analysis.ai_available ? <Badge variant="outline">Narration unavailable</Badge> : null}
          </div>
        </div>

        {analysis.entry_price ? (
          <dl className="grid grid-cols-2 gap-4 border-t border-border pt-4 text-sm sm:grid-cols-4">
            <div className="border-l-2 border-primary pl-2.5">
              <dt className="text-xs text-muted-foreground">Entry</dt>
              <dd className="font-medium tabular-nums">{formatPrice(analysis.entry_price)}</dd>
            </div>
            <div className="border-l-2 border-destructive pl-2.5">
              <dt className="text-xs text-muted-foreground">Stop Loss</dt>
              <dd className="font-medium tabular-nums">{formatPrice(analysis.stop_loss)}</dd>
            </div>
            <div className="border-l-2 border-success pl-2.5">
              <dt className="text-xs text-muted-foreground">Take Profit</dt>
              <dd className="font-medium tabular-nums">{formatPrice(analysis.take_profit)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Execution</dt>
              <dd className="font-medium">{formatEnumLabel(analysis.execution_guidance)}</dd>
            </div>
          </dl>
        ) : (
          <p className="border-t border-border pt-4 text-sm text-muted-foreground">
            No trade setup - the recommendation is WAIT.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
