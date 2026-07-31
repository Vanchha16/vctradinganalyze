import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { TechnicalAnalysisResponse, TrendDirection } from "@/services/types";

const TREND_VARIANT: Record<TrendDirection, "success" | "destructive" | "secondary"> = {
  bullish: "success",
  bearish: "destructive",
  sideways: "secondary",
};

export function TechnicalAnalysisCard({ data }: { data: TechnicalAnalysisResponse }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle>Technical Analysis</CardTitle>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant={TREND_VARIANT[data.trend]}>{data.trend}</Badge>
            <Badge variant="outline">{data.strength.replace("_", " ")}</Badge>
          </div>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold tabular-nums leading-none">{data.technical_score.toFixed(1)}</p>
          <p className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">Score</p>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <ScoreStat label="Trend" value={data.score_breakdown.trend} />
          <ScoreStat label="Momentum" value={data.score_breakdown.momentum} />
          <ScoreStat label="Oscillator" value={data.score_breakdown.oscillator} />
          <ScoreStat label="Volume" value={data.score_breakdown.volume} />
          <ScoreStat label="Volatility" value={data.score_breakdown.volatility} />
          <ScoreStat label="S/R" value={data.score_breakdown.support_resistance} />
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Support</p>
            <p className="mt-1 font-medium">
              {data.support ? `${data.support.price} (${data.support.source})` : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Resistance</p>
            <p className="mt-1 font-medium">
              {data.resistance ? `${data.resistance.price} (${data.resistance.source})` : "—"}
            </p>
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Indicators</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-sm">
            {Object.entries(data.indicators).map(([name, value]) => (
              <span key={name}>
                <span className="text-muted-foreground">{name}:</span> <span className="font-medium">{value.toFixed(2)}</span>
              </span>
            ))}
          </div>
        </div>

        {data.warnings.length > 0 ? (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2">
            <ul className="list-inside list-disc text-xs text-amber-700">
              {data.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ScoreStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-lg font-semibold tabular-nums">{value.toFixed(1)}</p>
    </div>
  );
}
