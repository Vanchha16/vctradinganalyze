import { confidenceLevelVariant } from "@/lib/badge-variants";
import { formatEnumLabel } from "@/lib/format";
import { cn } from "@/lib/utils";

const LEVEL_STROKE: Record<string, string> = {
  success: "stroke-success",
  warning: "stroke-warning",
  destructive: "stroke-destructive",
};

const RADIUS = 42;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

const SIZE_CLASSES = {
  md: { ring: "h-32 w-32", stroke: "10", text: "text-2xl", label: "text-xs" },
  sm: { ring: "h-14 w-14", stroke: "12", text: "text-sm", label: "text-[10px]" },
} as const;

/**
 * Radial progress ring for a 0-100 confidence score. Deliberately only
 * visualizes the number it's given - it does not call the separate
 * `/analysis/confidence/{symbol}` endpoint, since ADR-048 treats the AI
 * Orchestrator's confidence and the standalone Confidence Engine's
 * breakdown as distinct concepts that shouldn't be conflated here.
 *
 * `level` (the backend's `confidence_level` enum, e.g. `AIAnalysisResponse`)
 * is optional - `SignalResponse` has no equivalent field, only the raw
 * `confidence` number. When omitted, the ring's color falls back to a
 * fixed score-threshold (>=70 success / >=40 warning / below destructive)
 * - a presentation-only convention for coloring a progress ring, not a
 * reimplementation of the backend's confidence-level classification.
 *
 * `size="sm"` is a compact variant for inline use (e.g. `SignalCard`) -
 * same component/geometry, reused instead of a second gauge component.
 */
export function ConfidenceGauge({
  score,
  level,
  size = "md",
}: {
  score: number;
  level?: string;
  size?: "sm" | "md";
}) {
  const clamped = Math.max(0, Math.min(100, score));
  const offset = CIRCUMFERENCE * (1 - clamped / 100);
  const variant = level ? confidenceLevelVariant(level) : clamped >= 70 ? "success" : clamped >= 40 ? "warning" : "destructive";
  const strokeClass = LEVEL_STROKE[variant] ?? "stroke-primary";
  const { ring, stroke, text, label } = SIZE_CLASSES[size];

  return (
    <div className={cn("flex items-center", size === "sm" ? "gap-2" : "gap-4")}>
      <svg viewBox="0 0 100 100" className={cn(ring, "-rotate-90")}>
        <circle cx="50" cy="50" r={RADIUS} fill="none" strokeWidth={stroke} className="stroke-muted" />
        <circle
          cx="50"
          cy="50"
          r={RADIUS}
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          className={cn("transition-[stroke-dashoffset] duration-700 ease-out", strokeClass)}
        />
      </svg>
      <div className="flex flex-col gap-0.5">
        <p className={cn(text, "font-semibold tabular-nums")}>{clamped.toFixed(0)}%</p>
        {level ? (
          <p className={cn(label, "font-medium text-muted-foreground")}>{formatEnumLabel(level)} confidence</p>
        ) : (
          <p className={cn(label, "font-medium text-muted-foreground")}>Confidence</p>
        )}
      </div>
    </div>
  );
}
