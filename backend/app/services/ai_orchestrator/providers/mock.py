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
    calls: list[AIGenerationRequest] = field(default_factory=list)

    def generate(self, request: AIGenerationRequest) -> AIGenerationResponse:
        self.calls.append(request)
        if self.raises is not None:
            raise self.raises
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
        return AIGenerationResponse(raw_content=content, model_name="mock-model")

    def health_check(self) -> bool:
        return True
