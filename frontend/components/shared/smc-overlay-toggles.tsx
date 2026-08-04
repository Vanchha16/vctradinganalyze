"use client";

import { Box, Droplet, GitBranch, TrendingUp, Waves, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { SMC_OVERLAY_LABELS, type SmcOverlayKind } from "@/lib/smc-overlays";

const SMC_OVERLAY_ICONS: Record<SmcOverlayKind, LucideIcon> = {
  order_blocks: Box,
  fair_value_gaps: Waves,
  bos: TrendingUp,
  choch: GitBranch,
  liquidity: Droplet,
};

/**
 * Checkbox-like toggle group (implemented as clickable Badges) for the
 * SMC overlay kinds `buildSmcOverlays` supports - keeps charts from
 * dumping every overlay at once (ADR-107).
 */
export function SmcOverlayToggles({
  enabled,
  onToggle,
}: {
  enabled: ReadonlySet<SmcOverlayKind>;
  onToggle: (kind: SmcOverlayKind) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Chart overlay toggles">
      {(Object.keys(SMC_OVERLAY_LABELS) as SmcOverlayKind[]).map((kind) => {
        const isEnabled = enabled.has(kind);
        const Icon = SMC_OVERLAY_ICONS[kind];
        return (
          <button
            key={kind}
            type="button"
            aria-pressed={isEnabled}
            onClick={() => onToggle(kind)}
            className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded-full"
          >
            <Badge variant={isEnabled ? "default" : "outline"} className="cursor-pointer select-none gap-1">
              <Icon className="h-3 w-3" />
              {SMC_OVERLAY_LABELS[kind]}
            </Badge>
          </button>
        );
      })}
    </div>
  );
}
