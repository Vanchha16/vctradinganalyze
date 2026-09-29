import type { SignalResponse } from "@/services/types";

/**
 * smc-ict-crt-v1 decides by fixed rules and has no confidence score. The
 * backend stores its confidence as 0, meaning "not applicable" - so it is
 * never shown as "0%", which reads as "no confidence at all".
 * Presentation only: the stored value and every decision are unchanged.
 */
const RULE_BASED_STRATEGIES: ReadonlySet<string> = new Set(["smc_ict_crt_v1"]);

export const RULE_BASED_CONFIDENCE_LABEL = "Rule-based — No Score";

export function isRuleBasedSignal(
  signal: Pick<SignalResponse, "strategy">,
): boolean {
  return signal.strategy !== null && RULE_BASED_STRATEGIES.has(signal.strategy);
}
