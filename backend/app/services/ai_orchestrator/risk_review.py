"""AI risk review (ADR-167) - a second AI call on every BUY/SELL.

The deterministic tree still proposes the trade (ADR-078). This asks the
model one question a careful trader would ask before taking it - approve or
veto - and records the answer with its reasons.

What it may and may not do:
- It can only say approve or veto. It never proposes a direction, a price
  or a confidence, and the parser accepts nothing else.
- In `shadow` mode the verdict is recorded and nothing changes.
- In `enforce` mode a veto turns BUY/SELL into WAIT - a downgrade only,
  never the reverse.
- A failed or malformed review records no verdict and blocks nothing, in any
  mode - the same rule that keeps a narration failure from blocking an
  analysis (ADR-081).
"""

import json
from dataclasses import dataclass
from enum import StrEnum

from .providers.exceptions import MalformedAIResponseError

MAX_TOKENS = 600
_MAX_REASONS = 4
_MAX_REASON_WORDS = 40
_MAX_KEY_RISK_WORDS = 40
#: `ai_analysis.risk_review_key_risk` is String(400).
_MAX_KEY_RISK_CHARS = 400


class RiskReviewVerdict(StrEnum):
    APPROVE = "approve"
    VETO = "veto"


class RiskReviewMode(StrEnum):
    OFF = "off"
    SHADOW = "shadow"
    ENFORCE = "enforce"


@dataclass(frozen=True, slots=True)
class RiskReview:
    verdict: RiskReviewVerdict
    reasons: list[str]
    key_risk: str
    #: The mode it ran under - a shadow veto and an enforced veto mean very
    #: different things when looking back at a signal.
    mode: RiskReviewMode
    model_name: str
    input_tokens: int | None = None
    output_tokens: int | None = None


SYSTEM_PROMPT = (
    "You are a skeptical risk manager at a trading desk. A deterministic system "
    "has proposed the trade described below - its direction, entry, stop loss and "
    "take profit are fixed and you cannot change them. Your only decision: should "
    "a careful trader take this trade? Answer 'approve' or 'veto'. Veto only for "
    "concrete problems you can point to in the evidence given - for example a "
    "higher timeframe trending against the trade, a high-importance economic "
    "release close enough to hit it, a stop loss sitting inside nearby opposing "
    "structure, engines contradicting each other, or confidence resting on weak "
    "evidence. Do not veto merely because risk exists - every trade has risk. "
    "Never invent a price, indicator, news item or event that is not in the "
    "evidence. Give at most four short reasons, each tied to the evidence, and "
    "name the single biggest risk to this trade whatever your verdict. Respond "
    "only with the JSON schema you are given."
)

_JSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["approve", "veto"]},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "key_risk": {"type": "string"},
    },
    "required": ["verdict", "reasons", "key_risk"],
    "additionalProperties": False,
}


def json_schema() -> dict[str, object]:
    return _JSON_SCHEMA


def build_user_prompt(evidence: str) -> str:
    """`evidence` is the narration prompt itself (`prompt_builder`), so the
    review judges exactly the evidence the explanation is written from -
    higher timeframes, levels, events and news included."""
    return (
        f"{evidence}\n\n"
        "Review the proposed trade above. Approve it or veto it, with your reasons "
        "and the single biggest risk."
    )


def parse(raw_content: str) -> tuple[RiskReviewVerdict, list[str], str]:
    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise MalformedAIResponseError(f"risk review is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise MalformedAIResponseError("risk review JSON is not an object")

    raw_verdict = data.get("verdict")
    try:
        if not isinstance(raw_verdict, str):
            raise ValueError(raw_verdict)
        verdict = RiskReviewVerdict(raw_verdict)
    except ValueError as exc:
        raise MalformedAIResponseError(
            f"risk review has an unknown verdict: {raw_verdict!r}"
        ) from exc

    raw_reasons = data.get("reasons")
    if not isinstance(raw_reasons, list):
        raise MalformedAIResponseError("risk review reasons are not a list")
    reasons = [
        _cap(reason.strip(), _MAX_REASON_WORDS)
        for reason in raw_reasons
        if isinstance(reason, str) and reason.strip()
    ][:_MAX_REASONS]
    if not reasons:
        # A verdict with no reason cannot be checked against the evidence,
        # which is the only thing that makes a shadow verdict worth keeping.
        raise MalformedAIResponseError("risk review gave no reasons")

    key_risk = data.get("key_risk")
    if not isinstance(key_risk, str) or not key_risk.strip():
        raise MalformedAIResponseError("risk review gave no key risk")

    return verdict, reasons, _cap(key_risk.strip(), _MAX_KEY_RISK_WORDS)[:_MAX_KEY_RISK_CHARS]


def _cap(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


__all__ = [
    "MAX_TOKENS",
    "SYSTEM_PROMPT",
    "RiskReview",
    "RiskReviewMode",
    "RiskReviewVerdict",
    "build_user_prompt",
    "json_schema",
    "parse",
]
