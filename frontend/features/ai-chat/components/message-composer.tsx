"use client";

import { Send } from "lucide-react";
import { useEffect, useState } from "react";

import { SymbolTimeframePicker } from "@/components/shared/symbol-timeframe-picker";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Timeframe } from "@/services/types";

/**
 * Symbol/timeframe are explicit, optional fields here - never parsed
 * from the free-text message (ADR-095, docs/52 §5). Omitted, the
 * conversation's current `current_symbol`/`current_timeframe` are used
 * server-side.
 *
 * `prefill` lets `SuggestedPrompts` (rendered above this component, not
 * inside it) fill the textarea via a lifted callback on the page - no
 * state is duplicated, this just seeds the composer's own `content`.
 */
export function MessageComposer({
  onSend,
  isSending,
  defaultSymbol,
  prefill,
}: {
  onSend: (content: string, symbol?: string, timeframe?: Timeframe) => void;
  isSending: boolean;
  defaultSymbol?: string | null;
  prefill?: string | null;
}) {
  const [content, setContent] = useState("");
  const [symbol, setSymbol] = useState<string | null>(defaultSymbol ?? null);
  const [timeframe, setTimeframe] = useState<Timeframe>("h1");
  const [groundingOpen, setGroundingOpen] = useState(false);

  useEffect(() => {
    if (prefill) setContent(prefill);
  }, [prefill]);

  function handleSend() {
    if (!content.trim()) return;
    onSend(content.trim(), symbol ?? undefined, symbol ? timeframe : undefined);
    setContent("");
  }

  return (
    <div className="flex flex-col gap-2 border-t border-border p-4">
      {groundingOpen ? (
        <SymbolTimeframePicker
          symbol={symbol}
          timeframe={timeframe}
          onSymbolChange={setSymbol}
          onTimeframeChange={setTimeframe}
        />
      ) : (
        <button
          type="button"
          onClick={() => setGroundingOpen(true)}
          className="w-fit text-xs text-muted-foreground hover:text-foreground hover:underline"
        >
          {symbol ? `Grounded to ${symbol}` : "Ground this question to an asset (optional)"}
        </button>
      )}
      <div className="flex items-end gap-2">
        <Textarea
          value={content}
          onChange={(event) => setContent(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              handleSend();
            }
          }}
          placeholder="Ask about a recommendation, signal, or trading concept..."
          className="min-h-[52px] flex-1"
        />
        <Button onClick={handleSend} disabled={!content.trim() || isSending} aria-label="Send message">
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
