import { AiBadge } from "@/components/shared/ai-badge";
import { Markdown } from "@/components/shared/markdown-lazy";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { ReasoningResponse } from "@/services/types";

const SECTIONS: { key: keyof ReasoningResponse; label: string }[] = [
  { key: "summary", label: "Summary" },
  { key: "technical", label: "Technical" },
  { key: "smc", label: "SMC" },
  { key: "news", label: "News" },
  { key: "economic", label: "Economic" },
  { key: "risk", label: "Risk" },
  { key: "conclusion", label: "Conclusion" },
];

/**
 * docs/05 §12's Technical/SMC/News/Economic/Risk sections, organized as
 * tabs (docs/54 §3) - the only AI-generated field on the whole response
 * (ADR-079); every other field this page shows is deterministic.
 * Rendered through `react-markdown` (ADR-108, no `rehype-raw` - LLM text
 * only, never raw HTML).
 */
export function ReasoningSections({ reasoning }: { reasoning: ReasoningResponse }) {
  return (
    <Tabs defaultValue="summary">
      <div className="flex items-center justify-between gap-2">
        {/* Seven tabs are wider than a phone. `TabsList` is a non-shrinking
            inline-flex, so without this wrapper it ran past the card edge.
            The wrapper takes the remaining width (`min-w-0 flex-1`) and
            scrolls horizontally instead, with the scrollbar hidden since a
            swipe is the expected gesture on touch. */}
        <div className="min-w-0 flex-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <TabsList className="w-max">
            {SECTIONS.map((section) => (
              <TabsTrigger key={section.key} value={section.key}>
                {section.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>
        <div className="shrink-0">
          <AiBadge />
        </div>
      </div>
      {SECTIONS.map((section) => (
        <TabsContent key={section.key} value={section.key}>
          <Markdown>{reasoning[section.key]}</Markdown>
        </TabsContent>
      ))}
    </Tabs>
  );
}
