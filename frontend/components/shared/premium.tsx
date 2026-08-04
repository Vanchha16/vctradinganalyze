"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Presentation-only primitives that implement the premium design language
 * ported from the reference UI (https://alpha-trader-ai-42.lovable.app).
 * No data fetching lives here - every component takes plain props from
 * whatever real hook/query the call site already uses.
 */

/* ---------------- Count-up number ---------------- */
export function CountUp({
  value,
  decimals = 2,
  prefix = "",
  suffix = "",
  duration = 900,
  className,
}: {
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  duration?: number;
  className?: string;
}) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(value * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return (
    <span className={cn("num", className)}>
      {prefix}
      {display.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
      {suffix}
    </span>
  );
}

/* ---------------- Delta pill (up/down %) ---------------- */
export function Delta({
  value,
  suffix = "%",
  className,
  size = "sm",
}: {
  value: number;
  suffix?: string;
  className?: string;
  size?: "sm" | "md";
}) {
  const up = value >= 0;
  return (
    <span
      className={cn(
        "num inline-flex items-center gap-1 rounded-md font-medium tabular-nums transition-colors",
        size === "sm" ? "px-1.5 py-0.5 text-[11px]" : "px-2 py-1 text-xs",
        up ? "bg-bull/12 text-bull" : "bg-bear/12 text-bear",
        className,
      )}
    >
      <svg viewBox="0 0 8 8" className="size-2 fill-current">
        {up ? <path d="M4 0 8 6H0z" /> : <path d="M4 8 0 2h8z" />}
      </svg>
      {up ? "+" : ""}
      {value.toFixed(2)}
      {suffix}
    </span>
  );
}

/* ---------------- Panel (premium card) ---------------- */
export function Panel({
  className,
  children,
  hover = false,
  glow = false,
  ...rest
}: React.HTMLAttributes<HTMLDivElement> & { hover?: boolean; glow?: boolean }) {
  return (
    <div
      {...rest}
      className={cn(
        "card-premium relative overflow-hidden transition-all duration-300 ease-[cubic-bezier(.22,1,.36,1)]",
        hover && "cursor-pointer hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-lift",
        glow && "shadow-glow",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function PanelHeader({
  title,
  subtitle,
  right,
  icon,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border/70 px-5 py-4">
      <div className="flex items-center gap-3">
        {icon && <span className="grid size-8 place-items-center rounded-lg bg-surface-2 text-primary">{icon}</span>}
        <div>
          <h3 className="text-[13px] font-semibold tracking-tight text-foreground">{title}</h3>
          {subtitle && <p className="mt-0.5 text-[11px] text-muted-foreground">{subtitle}</p>}
        </div>
      </div>
      {right}
    </div>
  );
}

/* ---------------- Tag (semantic tone badge) ---------------- */
const toneMap: Record<string, string> = {
  bull: "bg-bull/12 text-bull border-bull/25",
  bear: "bg-bear/12 text-bear border-bear/25",
  warn: "bg-warn/12 text-warn border-warn/25",
  info: "bg-info/12 text-info border-info/25",
  brand: "bg-primary/12 text-primary border-primary/25",
  muted: "bg-surface-2 text-muted-foreground border-border",
};

export function Tag({
  children,
  tone = "muted",
  className,
}: {
  children: React.ReactNode;
  tone?: keyof typeof toneMap | string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
        toneMap[tone] ?? toneMap.muted,
        className,
      )}
    >
      {children}
    </span>
  );
}

export function LiveDot({ tone = "bull" }: { tone?: "bull" | "warn" | "bear" }) {
  const c = tone === "bull" ? "bg-bull" : tone === "warn" ? "bg-warn" : "bg-bear";
  return (
    <span className="relative flex size-1.5">
      <span className={cn("absolute inline-flex size-full rounded-full", c)} style={{ animation: "pulse-dot 1.8s ease-in-out infinite" }} />
      <span className={cn("relative inline-flex size-1.5 rounded-full", c)} />
    </span>
  );
}

/* ---------------- Skeleton (shimmer) ---------------- */
export function ShimmerSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn("skeleton", className)}>
      <div
        className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-foreground/6 to-transparent"
        style={{ animation: "shimmer 1.6s infinite" }}
      />
    </div>
  );
}

/* ---------------- Progress meter ---------------- */
export function Meter({
  value,
  tone = "brand",
  className,
}: {
  value: number;
  tone?: "brand" | "bull" | "bear" | "info" | "warn";
  className?: string;
}) {
  const [w, setW] = useState(0);
  useEffect(() => {
    const id = setTimeout(() => setW(value), 60);
    return () => clearTimeout(id);
  }, [value]);
  const bg = { brand: "bg-primary", bull: "bg-bull", bear: "bg-bear", info: "bg-info", warn: "bg-warn" }[tone];
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-surface-2", className)}>
      <div className={cn("h-full rounded-full transition-[width] duration-1000 ease-out", bg)} style={{ width: `${w}%` }} />
    </div>
  );
}

/* ---------------- Sparkline ---------------- */
export function Sparkline({
  data,
  width = 120,
  height = 34,
  tone,
  fill = true,
}: {
  data: number[];
  width?: number;
  height?: number;
  tone?: string;
  fill?: boolean;
}) {
  const ref = useRef<SVGPathElement>(null);
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1 || 1)) * width;
    const y = height - ((d - min) / span) * (height - 4) - 2;
    return [x, y] as const;
  });
  const path = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const up = (data[data.length - 1] ?? 0) >= (data[0] ?? 0);
  const color = tone ?? (up ? "var(--bull)" : "var(--bear)");
  const id = `sp-${Math.round((pts[0]?.[1] ?? 0) * 100)}-${data.length}-${up ? "u" : "d"}`;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const len = el.getTotalLength();
    el.style.strokeDasharray = `${len}`;
    el.style.strokeDashoffset = `${len}`;
    el.getBoundingClientRect();
    el.style.transition = "stroke-dashoffset 1.1s cubic-bezier(.22,1,.36,1)";
    el.style.strokeDashoffset = "0";
  }, [path]);

  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill && <path d={`${path} L${width},${height} L0,${height} Z`} fill={`url(#${id})`} stroke="none" />}
      <path ref={ref} d={path} fill="none" stroke={color} strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

/* ---------------- Segmented control ---------------- */
export function Segmented({
  options,
  value,
  onChange,
  size = "sm",
}: {
  options: string[];
  value: string;
  onChange: (v: string) => void;
  size?: "xs" | "sm";
}) {
  return (
    <div className="inline-flex items-center gap-0.5 rounded-lg border border-border bg-surface p-0.5">
      {options.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => onChange(o)}
          className={cn(
            "focus-ring rounded-md font-medium transition-all duration-200",
            size === "xs" ? "px-2 py-1 text-[11px]" : "px-2.5 py-1 text-xs",
            value === o ? "bg-surface-2 text-foreground shadow-[0_1px_0_0_oklch(1_0_0/8%)_inset]" : "text-muted-foreground hover:text-foreground",
          )}
        >
          {o}
        </button>
      ))}
    </div>
  );
}
