import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { MarketRegimeResponse, MarketRegimeState } from "@/services/types";

const REGIME_VARIANT: Record<MarketRegimeState, "success" | "destructive" | "secondary" | "warning"> = {
  trending_bullish: "success",
  trending_bearish: "destructive",
  ranging: "secondary",
  accumulation: "secondary",
  distribution: "secondary",
  breakout: "warning",
  pullback: "warning",
  reversal: "warning",
  high_volatility: "warning",
  low_volatility: "secondary",
  uncertain: "secondary",
};

export function MarketRegimeCard({ data }: { data: MarketRegimeResponse }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle>Market Regime</CardTitle>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant={REGIME_VARIANT[data.regime]}>{data.regime.replace("_", " ")}</Badge>
            <Badge variant="outline">{data.trend_regime.strength.replace("_", " ")} trend</Badge>
            <Badge variant="outline">{data.volatility.state.replace("_", " ")} volatility</Badge>
          </div>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold tabular-nums leading-none">{data.confidence.toFixed(1)}%</p>
          <p className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">Confidence</p>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <ScoreStat label="Trend Clarity" value={data.confidence_breakdown.trend_clarity} />
          <ScoreStat label="Volatility Clarity" value={data.confidence_breakdown.volatility_clarity} />
          <ScoreStat label="Structural" value={data.confidence_breakdown.structural_confirmation} />
        </div>

        <div className="text-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Top Candidates</p>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1.5">
            {data.candidates.map((candidate) => (
              <span key={candidate.regime}>
                {candidate.regime.replace("_", " ")}:{" "}
                <span className="font-medium tabular-nums">{candidate.confidence.toFixed(1)}</span>
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
