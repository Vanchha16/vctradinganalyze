import { Check, Circle } from "lucide-react";

import { formatDateTime, formatPrice } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SignalResponse } from "@/services/types";

const TERMINAL_STATUSES = new Set(["closed", "successful", "stopped_out", "expired", "cancelled"]);

/** Created -> Triggered -> Closed progression, using the signal's own timestamps. */
export function SignalStatusTimeline({ signal }: { signal: SignalResponse }) {
  const triggered = Boolean(signal.triggered_at);
  const closed = TERMINAL_STATUSES.has(signal.status);

  const steps = [
    { label: "Created", done: true, at: signal.created_at },
    { label: "Triggered", done: triggered, at: signal.triggered_at },
    { label: "Closed", done: closed, at: signal.closed_at },
  ];

  return (
    <div className="flex flex-col gap-3">
      <ol className="flex items-center gap-2">
        {steps.map((step, index) => (
          <li key={step.label} className="flex flex-1 items-center gap-2">
            {index > 0 ? <span className={cn("h-px flex-1", step.done ? "bg-primary" : "bg-border")} aria-hidden /> : null}
            <div className="flex flex-col items-center gap-1">
              {step.done ? (
                <Check className="h-4 w-4 rounded-full bg-primary p-0.5 text-primary-foreground" />
              ) : (
                <Circle className="h-4 w-4 text-muted-foreground" />
              )}
              <span className={cn("text-[10px]", step.done ? "text-foreground" : "text-muted-foreground")}>
                {step.label}
              </span>
            </div>
          </li>
        ))}
      </ol>
      <dl className="grid grid-cols-3 gap-2 text-xs text-muted-foreground">
        {steps.map((step) => (
          <div key={step.label}>
            <dt>{step.label}</dt>
            <dd className="font-medium text-foreground">{step.at ? formatDateTime(step.at) : "—"}</dd>
          </div>
        ))}
      </dl>
      {signal.profit_loss ? (
        <p className="text-sm">
          <span className="text-muted-foreground">Profit / Loss: </span>
          <span className={cn("font-medium tabular-nums", Number(signal.profit_loss) >= 0 ? "text-success" : "text-destructive")}>
            {formatPrice(signal.profit_loss)}
          </span>
        </p>
      ) : null}
      {/* ADR-166: a draft is an H1 setup waiting for M15 to confirm it. */}
      {signal.status === "draft" ? (
        <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
          Waiting for M15 to confirm the move. This signal is sent to Telegram and your EA only once
          it is confirmed.
        </p>
      ) : null}
      {signal.confirmed_at ? (
        <p className="text-xs text-muted-foreground">
          Confirmed {formatDateTime(signal.confirmed_at)}
          {signal.status_reason && signal.status !== "cancelled" ? ` · ${signal.status_reason}` : ""}
        </p>
      ) : null}
      {signal.status === "cancelled" && signal.status_reason ? (
        <p className="text-xs text-muted-foreground">Cancelled: {signal.status_reason}</p>
      ) : null}
    </div>
  );
}
