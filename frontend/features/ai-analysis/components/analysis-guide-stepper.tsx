import { Check, Search, Sparkles, type LucideIcon } from "lucide-react";
import { motion } from "framer-motion";

import { cn } from "@/lib/utils";

const STEPS: { label: string; icon: LucideIcon }[] = [
  { label: "Select Market", icon: Search },
  { label: "Generate", icon: Sparkles },
  { label: "Review", icon: Check },
];

/**
 * Lightweight 3-step guide (Select -> Generate -> Review) for the AI
 * Analysis landing page's picker -> generate -> history flow - purely
 * presentational, the page's existing state machine (symbol picked? /
 * generate pending? ) drives which step is "active".
 */
export function AnalysisGuideStepper({ step }: { step: 1 | 2 | 3 }) {
  return (
    <ol
      className="flex items-center gap-3 px-4 pt-4 text-sm text-muted-foreground sm:px-6 lg:px-8"
      aria-label="Analysis progress"
    >
      {STEPS.map(({ label, icon: Icon }, index) => {
        const stepNumber = index + 1;
        const isComplete = stepNumber < step;
        const isActive = stepNumber === step;
        return (
          <li key={label} className="flex items-center gap-2">
            {index > 0 ? (
              <span className="relative h-px w-8 overflow-hidden bg-border" aria-hidden>
                <motion.span
                  className="absolute inset-0 bg-primary"
                  initial={false}
                  animate={{ scaleX: stepNumber <= step ? 1 : 0 }}
                  style={{ originX: 0 }}
                  transition={{ duration: 0.25 }}
                />
              </span>
            ) : null}
            <span
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold transition-colors",
                isComplete && "border-primary bg-primary text-primary-foreground",
                isActive && !isComplete && "border-primary text-primary shadow-[0_0_0_3px] shadow-primary/15",
                !isActive && !isComplete && "border-border text-muted-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
            </span>
            <span className={cn(isActive && "font-medium text-foreground")}>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
