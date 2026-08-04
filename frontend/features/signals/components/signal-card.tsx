import { ArrowUpRight } from "lucide-react";
import { motion } from "framer-motion";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceGauge } from "@/features/ai-analysis/components/confidence-gauge";
import { BookmarkButton } from "@/features/signals/components/bookmark-button";
import { recommendationVariant, signalStatusVariant } from "@/lib/badge-variants";
import { formatEnumLabel, formatPrice, formatRelativeTime } from "@/lib/format";
import type { SignalResponse } from "@/services/types";

/**
 * docs/05 §11's Signal Card - Asset, Recommendation, Confidence, Entry,
 * Stop Loss, Take Profit, Timeframe, Status. Full "Reasoning" text lives
 * on the linked `ai_analysis` row, not the signal itself - shown on the
 * signal detail page (which fetches it), not duplicated per-card here to
 * avoid an N+1 fetch on list views.
 *
 * Not `<Card interactive>` - the card contains two separate click targets
 * (bookmark toggle, Details link), not one whole-card link, so the
 * `cursor-pointer` semantics of `interactive` don't apply. The hover lift
 * (docs/05 §19's "Cards" motion category) still applies as a pure visual
 * affordance via `whileHover`.
 */
export function SignalCard({ signal }: { signal: SignalResponse }) {
  return (
    <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.15 }}>
      <Card className="transition-shadow hover:shadow-md">
        <CardHeader className="space-y-0 pb-2">
          <div className="flex items-start justify-between gap-2">
            <div>
              <CardTitle>{signal.symbol}</CardTitle>
              <p className="text-xs text-muted-foreground">{signal.timeframe.toUpperCase()}</p>
            </div>
            <div className="flex items-center gap-1">
              <BookmarkButton signalId={signal.id} />
              <Link
                href={`/signals/${signal.id}`}
                className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
              >
                Details
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={recommendationVariant(signal.signal_type)}>{signal.signal_type.toUpperCase()}</Badge>
              <Badge variant={signalStatusVariant(signal.status)}>{formatEnumLabel(signal.status)}</Badge>
              {signal.profit_loss ? (
                <Badge variant={Number(signal.profit_loss) >= 0 ? "success" : "destructive"}>
                  P/L {formatPrice(signal.profit_loss)}
                </Badge>
              ) : null}
            </div>
            <ConfidenceGauge score={signal.confidence} size="sm" />
          </div>
          <dl className="grid grid-cols-2 gap-4 border-t border-border pt-3 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-muted-foreground/80">Entry</dt>
              <dd className="font-medium tabular-nums">{formatPrice(signal.entry_price)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground/80">Stop Loss</dt>
              <dd className="font-medium tabular-nums">{formatPrice(signal.stop_loss)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground/80">Take Profit</dt>
              <dd className="font-medium tabular-nums">{formatPrice(signal.take_profit)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground/80">Risk/Reward</dt>
              <dd className="font-medium tabular-nums">1:{signal.risk_reward.toFixed(2)}</dd>
            </div>
          </dl>
          <p className="text-xs text-muted-foreground">{formatRelativeTime(signal.created_at)}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
}
