"use client";

import { RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Panel, PanelHeader, Segmented } from "@/components/shared/premium";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConfirmActionDialog } from "@/features/admin/components/confirm-action-dialog";
import { useUpdateRuntimeSettings } from "@/hooks/use-runtime-settings";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";
import type {
  RuntimeSetting,
  RuntimeSettingGroup,
  RuntimeSettingListResponse,
  RuntimeSettingValue,
} from "@/services/types";

const STRATEGY_LABELS: Record<string, string> = {
  trend_following: "Trend following",
  smc: "Smart Money Concepts (SMC)",
  breakout: "Breakout",
  pullback: "Pullback",
  mean_reversion: "Mean reversion",
  scalping: "Scalping",
  swing_trading: "Swing trading",
  bbma: "BBMA",
};

const GROUPS: { group: RuntimeSettingGroup; title: string; subtitle: string }[] = [
  {
    group: "strategies",
    title: "Strategies",
    subtitle: "A switched-off strategy is still scored but can never be chosen. All off = every analysis is WAIT.",
  },
  {
    group: "tight",
    title: "Tight setups (ADR-176)",
    subtitle: "Fixed stop and target distances. Target must be at least 2x the stop.",
  },
  {
    group: "pipeline",
    title: "Signal pipeline",
    subtitle: "Confirmation, AI risk review and how long signals live. Changes affect every new signal.",
  },
];

type Draft = Record<string, RuntimeSettingValue>;

function same(a: RuntimeSettingValue, b: RuntimeSettingValue): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

function display(setting: RuntimeSetting, value: RuntimeSettingValue): string {
  if (setting.kind === "bool") return value ? "On" : "Off";
  if (setting.kind === "strategies") {
    const off = value as string[];
    return off.length ? `off: ${off.map((s) => STRATEGY_LABELS[s] ?? s).join(", ")}` : "all on";
  }
  return String(value);
}

/** Numbers are edited as text so a half-typed "7." does not jump back. */
function toPayload(setting: RuntimeSetting, value: RuntimeSettingValue): RuntimeSettingValue {
  if (setting.kind === "int") return Number(value);
  if (setting.kind === "decimal") return String(value).trim();
  return value;
}

/**
 * ADR-178. One draft across all three groups, saved as a single batch so a
 * stop and its target can move together. Saving and resetting both go
 * through a confirmation dialog that names every change - these values
 * change what the EA trades.
 */
export function RuntimeSettingsForm({ data }: { data: RuntimeSettingListResponse }) {
  const update = useUpdateRuntimeSettings();
  const byKey = useMemo(() => Object.fromEntries(data.items.map((s) => [s.key, s])), [data.items]);
  const server = useMemo<Draft>(() => Object.fromEntries(data.items.map((s) => [s.key, s.value])), [data.items]);
  const [draft, setDraft] = useState<Draft>(server);
  const [confirm, setConfirm] = useState<{ changes: Record<string, RuntimeSettingValue | null>; text: string } | null>(null);

  // A save replaces the server state; start the draft again from it.
  useEffect(() => setDraft(server), [server]);

  const dirty = data.items.filter((s) => !same(draft[s.key], s.value));

  function set(key: string, value: RuntimeSettingValue) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  function reviewSave() {
    const changes = Object.fromEntries(dirty.map((s) => [s.key, toPayload(s, draft[s.key])]));
    const text = dirty.map((s) => `${s.label}: ${display(s, s.value)} → ${display(s, draft[s.key])}`).join("; ");
    setConfirm({ changes, text });
  }

  function reviewReset(setting: RuntimeSetting) {
    setConfirm({
      changes: { [setting.key]: null },
      text: `${setting.label}: ${display(setting, setting.value)} → ${display(setting, setting.default)} (the .env default)`,
    });
  }

  async function apply() {
    if (!confirm) return;
    try {
      await update.mutateAsync({ changes: confirm.changes });
      toast.success(`Saved. Live within ${data.propagation_seconds} seconds.`);
      setConfirm(null);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Could not save the settings.");
    }
  }

  const disabled = (draft.disabled_strategies as string[]) ?? [];
  const strategies = byKey.disabled_strategies;

  return (
    <div className="flex flex-col gap-4">
      {GROUPS.map(({ group, title, subtitle }) => (
        <Panel key={group}>
          <PanelHeader title={title} subtitle={subtitle} />
          <div className="divide-y divide-border/70">
            {group === "strategies" && strategies ? (
              <>
                {strategies.choices.map((name) => {
                  const on = !disabled.includes(name);
                  return (
                    <Row key={name} label={STRATEGY_LABELS[name] ?? name}>
                      <Segmented
                        options={["On", "Off"]}
                        value={on ? "On" : "Off"}
                        onChange={(v) =>
                          set(
                            "disabled_strategies",
                            v === "On"
                              ? disabled.filter((d) => d !== name)
                              : strategies.choices.filter((c) => c === name || disabled.includes(c)),
                          )
                        }
                      />
                    </Row>
                  );
                })}
                <OverrideNote setting={strategies} onReset={() => reviewReset(strategies)} />
              </>
            ) : (
              data.items
                .filter((s) => s.group === group)
                .map((s) => (
                  <Row key={s.key} label={s.label} help={s.help} footer={<OverrideNote setting={s} onReset={() => reviewReset(s)} inline />}>
                    <Control setting={s} value={draft[s.key]} onChange={(v) => set(s.key, v)} />
                  </Row>
                ))
            )}
          </div>
        </Panel>
      ))}

      {/* Sticky to the content column, not fixed to the window, so it never
          depends on the sidebar's width or collapsed state. */}
      <div className="sticky bottom-3 z-20 rounded-xl border border-border bg-background/95 px-4 py-3 shadow-lg backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-[12px] text-muted-foreground">
            {dirty.length === 0
              ? `No unsaved changes. Saved changes go live within ${data.propagation_seconds} seconds, no restart. Every change is audit-logged.`
              : `${dirty.length} unsaved change${dirty.length === 1 ? "" : "s"}.`}
          </p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={dirty.length === 0} onClick={() => setDraft(server)}>
              Discard
            </Button>
            <Button size="sm" disabled={dirty.length === 0 || update.isPending} onClick={reviewSave}>
              Review &amp; save
            </Button>
          </div>
        </div>
      </div>

      <ConfirmActionDialog
        open={confirm !== null}
        onOpenChange={(open) => !open && setConfirm(null)}
        title="Change live trading settings?"
        description={`${confirm?.text ?? ""}. This affects signals the EA trades, within ${data.propagation_seconds} seconds.`}
        actionLabel="Apply"
        onConfirm={() => void apply()}
        isPending={update.isPending}
      />
    </div>
  );
}

function Row({
  label,
  help,
  footer,
  children,
}: {
  label: string;
  help?: string;
  footer?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 px-5 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="text-[13px] font-medium">{label}</p>
        {help ? <p className="mt-0.5 text-[11px] text-muted-foreground">{help}</p> : null}
        {footer}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

function Control({
  setting,
  value,
  onChange,
}: {
  setting: RuntimeSetting;
  value: RuntimeSettingValue;
  onChange: (v: RuntimeSettingValue) => void;
}) {
  if (setting.kind === "bool") {
    return <Segmented options={["On", "Off"]} value={value ? "On" : "Off"} onChange={(v) => onChange(v === "On")} />;
  }
  if (setting.kind === "choice") {
    return <Segmented options={setting.choices} value={String(value)} onChange={onChange} />;
  }
  return (
    <Input
      type="number"
      inputMode="decimal"
      className="w-28 text-right tabular-nums"
      min={setting.minimum ?? undefined}
      max={setting.maximum ?? undefined}
      step={setting.kind === "int" ? 1 : 0.5}
      value={String(value)}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function OverrideNote({
  setting,
  onReset,
  inline = false,
}: {
  setting: RuntimeSetting;
  onReset: () => void;
  inline?: boolean;
}) {
  if (!setting.overridden) return null;
  return (
    <div className={inline ? "mt-1.5 flex flex-wrap items-center gap-2" : "flex flex-wrap items-center gap-2 px-5 py-3"}>
      <Badge variant="warning">Changed from .env</Badge>
      <span className="text-[11px] text-muted-foreground">default: {display(setting, setting.default)}</span>
      <Button variant="ghost" size="sm" onClick={onReset}>
        <RotateCcw className="mr-1 size-3.5" />
        Reset to default
      </Button>
    </div>
  );
}
