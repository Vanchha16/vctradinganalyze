import { Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * Marks content as AI-generated (docs/56 §9) - mirrors the backend's
 * existing deterministic-vs-AI-generated boundary (ADR-078/079: only the
 * narrative reasoning text is LLM-generated, every number is deterministic)
 * by making that boundary visible in the UI for the first time. Visual
 * marker only - adds no data, changes no logic.
 */
export function AiBadge({ className }: { className?: string }) {
  return (
    <Badge variant="secondary" className={cn("gap-1 font-medium text-muted-foreground", className)}>
      <Sparkles className="h-3 w-3" />
      AI
    </Badge>
  );
}
