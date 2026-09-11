"""Test-only `AIProvider` injection (docs/50 §8, ADR-081) - mirrors
`httpx.MockTransport`'s role in `test_news_ai_summary_generator.py`, not
a production fallback. Never used by `app/dependencies/ai_orchestrator.py`."""

import json
from dataclasses import dataclass, field

from .base import AIGenerationRequest, AIGenerationResponse
from .exceptions import AIProviderError


@dataclass
class MockAIProvider:
    name: str = "mock"
    response_content: str | None = None
    raises: AIProviderError | None = None
    #: ADR-167 - what a risk review request (recognised by its `verdict`
    #: schema) gets back. Defaults to an approval, so existing tests that
    #: produce a BUY/SELL see no behaviour change.
    review_content: str | None = None
    #: ADR-149 - what this fake provider claims it spent. `None` by
    #: default, matching a provider that reports no usage block.
    input_tokens: int | None = None
    output_tokens: int | None = None
    calls: list[AIGenerationRequest] = field(default_factory=list)

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        self.calls.append(request)
        if self.raises is not None:
            raise self.raises

        properties = request.json_schema.get("properties", {})
        if isinstance(properties, dict) and "verdict" in properties:
            content = self.review_content or json.dumps(
                {"verdict": "approve", "reasons": ["Mock reason."], "key_risk": "Mock key risk."}
            )
        else:
            content = self.response_content or json.dumps(
                {
                    "summary": "Mock summary.",
                    "technical": "Mock technical.",
                    "smc": "Mock smc.",
                    "economic": "Mock economic.",
                    "news": "Mock news.",
                    "risk": "Mock risk.",
                    "conclusion": "Mock conclusion.",
                }
            )
        return AIGenerationResponse(
            raw_content=content,
            model_name="mock-model",
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
        )

    def health_check(self) -> bool:
        return True
