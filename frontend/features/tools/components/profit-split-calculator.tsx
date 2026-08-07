"use client";

import { Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Panel, PanelHeader } from "@/components/shared/premium";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Contributor {
  id: number;
  name: string;
  amount: string;
}

const PALETTE = ["#ffb454", "#6ee7b7", "#7fb3ff", "#fb7185", "#c9a4ff", "#5fd4d4"];

let nextId = 3;

const INITIAL_CONTRIBUTORS: Contributor[] = [
  { id: 1, name: "Person A", amount: "108" },
  { id: 2, name: "Person B", amount: "40" },
];

/**
 * Splits a final pot proportionally across contributors by their
 * original stake, so every contributor earns the same rate of return
 * on their own stake regardless of stake size - the dollar payout
 * differs, the percentage return doesn't. Standalone client-side tool,
 * no backend involved (nothing here is persisted or asset/signal
 * related).
 */
export function ProfitSplitCalculator() {
  const [contributors, setContributors] = useState<Contributor[]>(INITIAL_CONTRIBUTORS);
  const [pot, setPot] = useState("1000");

  function addContributor() {
    setContributors((prev) => [...prev, { id: nextId++, name: "", amount: "" }]);
  }

  function removeContributor(id: number) {
    setContributors((prev) => (prev.length > 2 ? prev.filter((c) => c.id !== id) : prev));
  }

  function updateContributor(id: number, field: "name" | "amount", value: string) {
    setContributors((prev) => prev.map((c) => (c.id === id ? { ...c, [field]: value } : c)));
  }

  const result = useMemo(() => {
    const entries = contributors.map((c, i) => ({
      name: c.name.trim() || `Person ${i + 1}`,
      amount: Number.parseFloat(c.amount) || 0,
      color: PALETTE[i % PALETTE.length],
    }));
    const potValue = Number.parseFloat(pot) || 0;
    const total = entries.reduce((sum, e) => sum + e.amount, 0);

    if (entries.some((e) => e.amount < 0) || potValue < 0) {
      return { error: "All values must be non-negative numbers." } as const;
    }
    if (total <= 0) {
      return { error: "Contributions must sum to more than $0." } as const;
    }

    const shares = entries.map((e) => ({
      ...e,
      pct: (e.amount / total) * 100,
      payout: potValue * (e.amount / total),
    }));
    const overallReturnPct = ((potValue - total) / total) * 100;

    return { shares, potValue, overallReturnPct } as const;
  }, [contributors, pot]);

  return (
    <div className="flex flex-col gap-4">
      <Panel>
        <PanelHeader title="Contributors" subtitle="Who put in what" />
        <div className="flex flex-col gap-3 p-4">
          {contributors.map((c, i) => (
            <div key={c.id} className="flex items-center gap-2">
              <span className="w-6 text-right text-[11px] tabular-nums text-muted-foreground">
                {String(i + 1).padStart(2, "0")}
              </span>
              <Input
                placeholder={`Person ${i + 1}`}
                value={c.name}
                onChange={(e) => updateContributor(c.id, "name", e.target.value)}
                className="flex-1"
              />
              <div className="relative w-36">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                  $
                </span>
                <Input
                  type="number"
                  min={0}
                  step="any"
                  placeholder="0.00"
                  value={c.amount}
                  onChange={(e) => updateContributor(c.id, "amount", e.target.value)}
                  className="pl-6 text-right tabular-nums"
                />
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="w-8 px-0 text-muted-foreground hover:text-destructive"
                disabled={contributors.length <= 2}
                onClick={() => removeContributor(c.id)}
                aria-label={`Remove ${c.name || `Person ${i + 1}`}`}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <Button type="button" variant="outline" size="sm" onClick={addContributor} className="mt-1">
            <Plus className="mr-2 h-3.5 w-3.5" />
            Add contributor
          </Button>
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Final Pot" subtitle="Total after trading / activity" />
        <div className="flex items-center justify-between gap-4 p-4">
          <Label htmlFor="pot" className="text-xs text-muted-foreground">
            Total after trading / activity
          </Label>
          <div className="relative w-44">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
              $
            </span>
            <Input
              id="pot"
              type="number"
              min={0}
              step="any"
              value={pot}
              onChange={(e) => setPot(e.target.value)}
              className="pl-6 text-right tabular-nums"
            />
          </div>
        </div>
        {"error" in result ? (
          <p className="px-4 pb-4 text-xs text-destructive">{result.error}</p>
        ) : null}
      </Panel>

      {"error" in result ? null : (
        <Panel>
          <PanelHeader title="Return on Contribution" subtitle="Same rate for every contributor" />
          <div className="flex flex-col gap-5 p-4">
            <div className="flex items-center justify-between rounded-lg border border-border bg-surface p-4">
              <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                Return %
                <p className="mt-1 text-[10px] font-normal normal-case text-muted-foreground/80">
                  same rate for every contributor, regardless of stake size
                </p>
              </div>
              <div
                className={cn(
                  "text-3xl font-semibold tabular-nums",
                  result.overallReturnPct > 0
                    ? "text-bull"
                    : result.overallReturnPct < 0
                      ? "text-bear"
                      : "text-muted-foreground",
                )}
              >
                {result.overallReturnPct > 0 ? "+" : ""}
                {result.overallReturnPct.toFixed(1)}%
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Allocation</p>
              {result.shares.map((s) => (
                <div key={s.name} className="grid grid-cols-[90px_1fr_48px] items-center gap-3">
                  <span className="truncate text-right text-xs text-muted-foreground">{s.name}</span>
                  <div className="h-3 overflow-hidden rounded-full bg-surface-2">
                    <div
                      className="h-full rounded-full transition-[width] duration-500"
                      style={{ width: `${s.pct}%`, backgroundColor: s.color }}
                    />
                  </div>
                  <span className="text-right text-xs font-medium tabular-nums">{s.pct.toFixed(1)}%</span>
                </div>
              ))}
            </div>

            <div className="flex flex-col divide-y divide-border/70 border-t border-border pt-2">
              <div className="grid grid-cols-[16px_1fr_70px_90px] gap-3 pb-2 text-[10px] uppercase tracking-wide text-muted-foreground">
                <span />
                <span>Contributor</span>
                <span className="text-right">Share</span>
                <span className="text-right">Payout</span>
              </div>
              {result.shares.map((s) => (
                <div key={s.name} className="grid grid-cols-[16px_1fr_70px_90px] items-center gap-3 py-2.5">
                  <span className="size-2.5 rounded-sm" style={{ backgroundColor: s.color }} />
                  <div>
                    <p className="text-[13px] text-foreground">{s.name}</p>
                    <p className="text-[10px] text-muted-foreground">in {formatCurrency(s.amount)}</p>
                  </div>
                  <span className="text-right text-xs tabular-nums text-muted-foreground">
                    {s.pct.toFixed(2)}%
                  </span>
                  <span className="text-right text-sm font-semibold tabular-nums text-primary">
                    {formatCurrency(s.payout)}
                  </span>
                </div>
              ))}
            </div>

            <div className="flex items-baseline justify-between border-t border-border pt-3">
              <span className="text-[11px] uppercase tracking-wide text-muted-foreground">Final Pot</span>
              <span className="text-xl font-semibold tabular-nums">{formatCurrency(result.potValue)}</span>
            </div>

            <p className="border-t border-dashed border-border pt-3 text-[11px] leading-relaxed text-muted-foreground">
              Every contributor earns the same return rate on their own stake in a proportional
              split — the dollar payout differs, the percentage doesn&rsquo;t.
            </p>
          </div>
        </Panel>
      )}
    </div>
  );
}
