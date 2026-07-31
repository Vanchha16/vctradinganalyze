import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { MarketStructureState, SMCAnalysisResponse } from "@/services/types";

const STRUCTURE_VARIANT: Record<MarketStructureState, "success" | "destructive" | "secondary"> = {
  bullish: "success",
  bearish: "destructive",
  range: "secondary",
  transition: "secondary",
};

export function SmcCard({ data }: { data: SMCAnalysisResponse }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle>Smart Money Concepts</CardTitle>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant={STRUCTURE_VARIANT[data.market_structure.state]}>{data.market_structure.state}</Badge>
            <Badge variant="outline">{data.premium_discount.position}</Badge>
          </div>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold tabular-nums leading-none">{data.smc_score.toFixed(1)}</p>
          <p className="mt-1 text-xs uppercase tracking-wide text-muted-foreground">Score</p>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <CountStat label="BOS" value={data.bos.length} />
          <CountStat label="CHOCH" value={data.choch.length} />
          <CountStat label="Order Blocks" value={data.order_blocks.length} />
          <CountStat label="FVGs" value={data.fair_value_gaps.length} />
          <CountStat label="Liquidity Zones" value={data.liquidity_zones.length} />
          <CountStat label="Liquidity Sweeps" value={data.liquidity_sweeps.length} />
        </div>

        <div className="text-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Confluence</p>
          <p className="mt-1">
            <span className="font-semibold tabular-nums">{data.confluence.confluence_score.toFixed(1)}</span> —{" "}
            {data.confluence.factors.length > 0 ? data.confluence.factors.join(", ") : "no factors"}
          </p>
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

function CountStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}
