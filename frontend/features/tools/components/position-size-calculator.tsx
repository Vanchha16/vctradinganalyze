"use client";

import { ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Panel, PanelHeader } from "@/components/shared/premium";
import { formatCurrency } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Computes the max number of same-size positions an account can open
 * given its balance, leverage, and one position's notional value
 * (lot size × contract size × price). Standalone client-side tool - no
 * backend involved, nothing here is persisted.
 *
 * One assumption baked in: this applies the account's headline
 * leverage (1:X) straight to the formula. Brokers frequently cap
 * leverage on specific instruments (e.g. XAUUSD) well below the
 * account's displayed number - if real positions get rejected before
 * hitting this tool's predicted count, check the platform's actual
 * used margin on one open position to find the real per-instrument cap.
 */
export function PositionSizeCalculator() {
  const [balance, setBalance] = useState("5000");
  const [leverage, setLeverage] = useState("2000");
  const [lotSize, setLotSize] = useState("2.5");
  const [contractSize, setContractSize] = useState("100");
  const [price, setPrice] = useState("4266");
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const result = useMemo(() => {
    const balanceNum = Number.parseFloat(balance) || 0;
    const leverageNum = Number.parseFloat(leverage) || 1;
    const lotSizeNum = Number.parseFloat(lotSize) || 0;
    const contractNum = Number.parseFloat(contractSize) || 0;
    const priceNum = Number.parseFloat(price) || 0;

    const notional = lotSizeNum * contractNum * priceNum;
    const marginPerPosition = notional / leverageNum;
    const maxPositions = marginPerPosition > 0 ? Math.floor(balanceNum / marginPerPosition) : 0;

    return { balanceNum, leverageNum, lotSizeNum, contractNum, priceNum, notional, marginPerPosition, maxPositions };
  }, [balance, leverage, lotSize, contractSize, price]);

  return (
    <div className="flex flex-col gap-4">
      <Panel>
        <PanelHeader title="Your numbers" subtitle="Defaults set for XAUUSD (gold)" />
        <div className="flex flex-col gap-4 p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="balance">Balance ($)</Label>
              <Input
                id="balance"
                type="number"
                step="0.01"
                value={balance}
                onChange={(e) => setBalance(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="leverage">Leverage (1:X)</Label>
              <Input
                id="leverage"
                type="number"
                step="1"
                value={leverage}
                onChange={(e) => setLeverage(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="lotSize">Lot size</Label>
              <Input
                id="lotSize"
                type="number"
                step="0.01"
                value={lotSize}
                onChange={(e) => setLotSize(e.target.value)}
              />
            </div>
          </div>

          <button
            type="button"
            onClick={() => setAdvancedOpen((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-primary"
          >
            <ChevronRight className={cn("h-3 w-3 transition-transform", advancedOpen && "rotate-90")} />
            Advanced: contract size &amp; price (defaults set for XAUUSD)
          </button>

          {advancedOpen ? (
            <div className="grid grid-cols-1 gap-3 border-t border-border pt-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="contract">Contract size (oz/lot)</Label>
                <Input
                  id="contract"
                  type="number"
                  step="1"
                  value={contractSize}
                  onChange={(e) => setContractSize(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="price">Gold price ($/oz)</Label>
                <Input
                  id="price"
                  type="number"
                  step="0.01"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
              </div>
            </div>
          ) : null}
        </div>
      </Panel>

      <Panel>
        <div className="flex flex-col items-center gap-1 p-6 text-center">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Max positions you can open
          </p>
          <p className="text-5xl font-bold tabular-nums text-primary">
            {result.maxPositions.toLocaleString()}
          </p>
          <p className="text-sm text-muted-foreground">at {result.lotSizeNum} lots each</p>
        </div>
        <div className="grid grid-cols-2 gap-3 px-4 pb-4">
          <div className="rounded-lg border border-border bg-surface p-3.5">
            <p className="text-[10.5px] uppercase tracking-wide text-muted-foreground">
              Notional per position
            </p>
            <p className="mt-1 text-lg font-semibold tabular-nums">{formatCurrency(result.notional)}</p>
          </div>
          <div className="rounded-lg border border-border bg-surface p-3.5">
            <p className="text-[10.5px] uppercase tracking-wide text-muted-foreground">
              Margin per position
            </p>
            <p className="mt-1 text-lg font-semibold tabular-nums">
              {formatCurrency(result.marginPerPosition)}
            </p>
          </div>
        </div>
        <div className="mx-4 mb-4 rounded-lg border border-border bg-surface p-3.5 font-mono text-xs leading-7 text-muted-foreground">
          margin/position <span className="text-primary">=</span> ({result.lotSizeNum}{" "}
          <span className="text-primary">×</span> {result.contractNum.toLocaleString()}{" "}
          <span className="text-primary">×</span> {result.priceNum}) <span className="text-primary">÷</span>{" "}
          {result.leverageNum} <span className="text-primary">=</span>{" "}
          <span className="font-semibold text-foreground">{formatCurrency(result.marginPerPosition)}</span>
          <br />
          max positions <span className="text-primary">=</span> {formatCurrency(result.balanceNum)}{" "}
          <span className="text-primary">÷</span> {formatCurrency(result.marginPerPosition)}{" "}
          <span className="text-primary">=</span>{" "}
          <span className="font-semibold text-foreground">{result.maxPositions}</span>
        </div>
        <p className="border-t border-border p-4 text-[11px] leading-relaxed text-muted-foreground">
          <strong className="text-foreground">One assumption still baked in:</strong> this applies your
          account leverage (1:X) straight to the formula. Brokers frequently cap leverage on specific
          instruments (e.g. XAUUSD) well below the account&rsquo;s headline number. If your positions are
          getting rejected before hitting this tool&rsquo;s predicted count, check your platform&rsquo;s
          actual used margin on one open position to find the real cap for that instrument.
        </p>
      </Panel>
    </div>
  );
}
