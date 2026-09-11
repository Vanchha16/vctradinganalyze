"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ConfirmActionDialog } from "@/features/admin/components/confirm-action-dialog";
import { useUpdateEaSettings } from "@/hooks/use-ea-tokens";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type { EaSettings, EaTokenResponse } from "@/services/types";

interface FormState {
  paused: boolean;
  dry_run: boolean;
  lot_size: string;
  max_open_trades: string;
  max_slippage_points: string;
}

function toForm(token: EaTokenResponse): FormState {
  return {
    paused: token.settings.paused,
    dry_run: token.settings.dry_run,
    lot_size: token.settings.lot_size.toFixed(2),
    max_open_trades: String(token.settings.max_open_trades),
    max_slippage_points: String(token.settings.max_slippage_points),
  };
}

/** Returns the settings to send, or an error message for the first bad field. */
function validate(form: FormState, maxLot: number | null): EaSettings | string {
  const lot = Number(form.lot_size);
  if (!Number.isFinite(lot) || lot <= 0) return "Lot size must be above 0.";
  if (Math.abs(Math.round(lot * 100) - lot * 100) > 1e-6) return "Lot size must be in steps of 0.01.";
  if (maxLot !== null && lot > maxLot + 1e-9) {
    return `Lot size is above this EA's hard limit of ${maxLot.toFixed(2)}. Raise MaxLotSize in the EA on the server first.`;
  }
  const trades = Number(form.max_open_trades);
  if (!Number.isInteger(trades) || trades < 1 || trades > 20) return "Max open trades must be a whole number from 1 to 20.";
  const slippage = Number(form.max_slippage_points);
  if (!Number.isInteger(slippage) || slippage < 0 || slippage > 1000) {
    return "Max slippage must be a whole number from 0 to 1000 points.";
  }
  return {
    paused: form.paused,
    dry_run: form.dry_run,
    lot_size: Math.round(lot * 100) / 100,
    max_open_trades: trades,
    max_slippage_points: slippage,
  };
}

/**
 * ADR-163 - edits the settings one terminal picks up on its next poll.
 * Switching to live asks for confirmation first, and warns when the EA on
 * the server has not allowed the website to do that (it would stay in dry
 * run). The EA's hard lot limit is shown and enforced here as well as in
 * the EA itself.
 */
export function EaSettingsDialog({
  token,
  open,
  onOpenChange,
}: {
  token: EaTokenResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const updateSettings = useUpdateEaSettings();
  const [form, setForm] = useState<FormState | null>(null);
  const [confirmLive, setConfirmLive] = useState(false);

  // Reset from the saved settings each time the dialog opens - not on every
  // background refetch, which would wipe an edit in progress.
  const tokenId = token?.id;
  useEffect(() => {
    if (open && token) setForm(toForm(token));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, tokenId]);

  if (!token || !form) return null;

  const maxLot = token.terminal.max_lot;
  const liveBlocked = !form.dry_run && token.terminal.allow_remote_live === false;
  const liveUnknown = !form.dry_run && token.terminal.allow_remote_live === null;
  const switchingToLive = token.settings.dry_run && !form.dry_run;

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  async function save(settings: EaSettings) {
    if (!token) return;
    try {
      await updateSettings.mutateAsync({ id: token.id, settings });
      toast.success("Saved. The EA applies it on its next check, within about 10 seconds.");
      setConfirmLive(false);
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not save the EA settings.");
    }
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!form) return;
    const result = validate(form, maxLot);
    if (typeof result === "string") {
      toast.error(result);
      return;
    }
    if (switchingToLive) {
      setConfirmLive(true);
      return;
    }
    void save(result);
  }

  const pending = validate(form, maxLot);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>EA settings · {token.name}</DialogTitle>
            <DialogDescription>
              Applied by the Expert Advisor on its next check. Token, API URL and magic number stay
              in MT5.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label>Trading</Label>
                <Select
                  value={form.paused ? "paused" : "active"}
                  onValueChange={(value) => update("paused", value === "paused")}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="paused">Paused</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Mode</Label>
                <Select
                  value={form.dry_run ? "dry" : "live"}
                  onValueChange={(value) => update("dry_run", value === "dry")}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dry">Dry run (no orders)</SelectItem>
                    <SelectItem value="live">Live (real money)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {form.paused ? (
              <p className="text-xs text-muted-foreground">
                Paused: no new orders, and the EA cancels its own unfilled orders. Open positions keep
                their stop loss and take profit.
              </p>
            ) : null}

            {liveBlocked ? (
              <p className="flex gap-2 rounded-md border border-warning/30 bg-warning/10 p-2.5 text-xs text-warning">
                <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                This EA has not allowed the website to switch it to live, so it will stay in dry run.
                Set AllowWebsiteLive = true in the EA&apos;s inputs on the server first.
              </p>
            ) : liveUnknown ? (
              <p className="flex gap-2 rounded-md border border-warning/30 bg-warning/10 p-2.5 text-xs text-warning">
                <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                This EA has not reported whether it allows a live switch (it needs version 1.20 or
                later). It stays in dry run unless AllowWebsiteLive = true on the server.
              </p>
            ) : null}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="ea-lot">Lot size</Label>
                <Input
                  id="ea-lot"
                  type="number"
                  inputMode="decimal"
                  step="0.01"
                  min="0.01"
                  max={maxLot ?? undefined}
                  value={form.lot_size}
                  onChange={(event) => update("lot_size", event.target.value)}
                />
                <span className="text-[11px] text-muted-foreground">
                  {maxLot !== null ? `EA limit ${maxLot.toFixed(2)}` : "EA limit not reported"}
                </span>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="ea-trades">Max open trades</Label>
                <Input
                  id="ea-trades"
                  type="number"
                  inputMode="numeric"
                  step="1"
                  min="1"
                  max="20"
                  value={form.max_open_trades}
                  onChange={(event) => update("max_open_trades", event.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="ea-slippage">Max slippage</Label>
                <Input
                  id="ea-slippage"
                  type="number"
                  inputMode="numeric"
                  step="1"
                  min="0"
                  max="1000"
                  value={form.max_slippage_points}
                  onChange={(event) => update("max_slippage_points", event.target.value)}
                />
                <span className="text-[11px] text-muted-foreground">points</span>
              </div>
            </div>

            {typeof pending === "string" ? <p className="text-xs text-destructive">{pending}</p> : null}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant={switchingToLive ? "destructive" : "default"}
                disabled={updateSettings.isPending || typeof pending === "string"}
              >
                {updateSettings.isPending ? "Saving..." : switchingToLive ? "Switch to live" : "Save"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <ConfirmActionDialog
        open={confirmLive}
        onOpenChange={setConfirmLive}
        title="Switch to LIVE trading?"
        description={`Every new signal will place a REAL order of ${form.lot_size} lot on this account, with real money. ${
          liveBlocked || liveUnknown
            ? "The EA will stay in dry run until AllowWebsiteLive = true is set on the server."
            : "This takes effect on the EA's next check."
        }`}
        actionLabel="Yes, go live"
        variant="destructive"
        onConfirm={() => {
          const result = validate(form, maxLot);
          if (typeof result !== "string") void save(result);
        }}
        isPending={updateSettings.isPending}
      />
    </>
  );
}

/** One line under each token: what the terminal is doing, and whether it
 * is running the latest saved settings. */
export function EaTerminalSummary({ token }: { token: EaTokenResponse }) {
  const { settings, terminal } = token;

  if (!terminal.ea_version) {
    return (
      <p className="text-xs text-muted-foreground">
        Website settings need EA 1.20 or later - this terminal has not reported yet.
      </p>
    );
  }

  const mode = terminal.paused ? "Paused" : terminal.dry_run === false ? "Live" : "Dry run";
  // The EA reports version 0 while it runs on its own inputs
  // (UseWebsiteSettings = false) - that is not "waiting", it will never apply.
  const usingInputs = terminal.applied_settings_version === 0;
  const applied = terminal.applied_settings_version === settings.version;
  const liveBlocked = !settings.dry_run && terminal.dry_run !== false && terminal.allow_remote_live === false;
  // MaxLotSize can be lowered on the server after a larger lot was saved;
  // the EA then quietly trades the smaller one.
  const lotCapped = terminal.max_lot !== null && settings.lot_size > terminal.max_lot + 1e-9;

  return (
    <div className="flex flex-wrap items-center gap-1.5 text-xs">
      <Badge variant={mode === "Live" ? "warning" : mode === "Paused" ? "destructive" : "outline"}>{mode}</Badge>
      <span className="text-muted-foreground">
        EA {terminal.ea_version} · lot {settings.lot_size.toFixed(2)}
        {terminal.max_lot !== null ? ` (limit ${terminal.max_lot.toFixed(2)})` : ""} · max {settings.max_open_trades}{" "}
        trade{settings.max_open_trades === 1 ? "" : "s"}
      </span>
      {usingInputs ? (
        <Badge variant="secondary" title="UseWebsiteSettings is false on this EA, so it ignores these settings">
          Using EA inputs
        </Badge>
      ) : applied ? (
        <Badge variant="success">Settings applied</Badge>
      ) : (
        <Badge variant="secondary">Waiting for EA · v{settings.version}</Badge>
      )}
      {liveBlocked ? <span className="text-warning">Live not allowed on the server</span> : null}
      {lotCapped ? <span className="text-warning">EA caps the lot at {terminal.max_lot?.toFixed(2)}</span> : null}
    </div>
  );
}
