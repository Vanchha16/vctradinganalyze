import { LineChart, Layers, Newspaper, ShieldAlert, type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

const PROMPT_ICONS: LucideIcon[] = [LineChart, Layers, ShieldAlert, Newspaper];

const GENERAL_PROMPTS = [
  "What's the current technical outlook?",
  "Explain the Smart Money Concepts setup here.",
  "What are the key risks with this trade?",
  "Summarize the latest news impact on this asset.",
];

const GROUNDED_PROMPTS = [
  "What's the technical outlook for {symbol}?",
  "Explain the SMC setup for {symbol}.",
  "What's the confidence and risk level for {symbol}?",
  "Summarize recent news affecting {symbol}.",
];

/** Static curated prompt templates shown on empty/new conversations - no backend. */
export function SuggestedPrompts({
  symbol,
  onSelect,
}: {
  symbol?: string | null;
  onSelect: (prompt: string) => void;
}) {
  const prompts = (symbol ? GROUNDED_PROMPTS : GENERAL_PROMPTS).map((prompt) =>
    symbol ? prompt.replace("{symbol}", symbol) : prompt,
  );

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Try asking</p>
      <div className="flex flex-wrap gap-2">
        {prompts.map((prompt, index) => {
          const Icon = PROMPT_ICONS[index];
          return (
            <Button key={prompt} variant="secondary" onClick={() => onSelect(prompt)}>
              {Icon ? <Icon className="mr-2 h-4 w-4" /> : null}
              {prompt}
            </Button>
          );
        })}
      </div>
    </div>
  );
}
