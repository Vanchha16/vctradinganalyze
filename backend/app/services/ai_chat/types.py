"""Public result type for `AIChatEngine` (docs/52 §7). Everything else
this engine needs (`AnalysisContext`, `AIAnalysis`, `Signal`) is already
defined elsewhere and reused as-is - no parallel evidence types here."""

from dataclasses import dataclass, field

from app.models.message import Message


@dataclass(frozen=True, slots=True)
class ChatExchange:
    """One question/answer round-trip - both persisted `Message` rows
    (ADR-096)."""

    user_message: Message
    assistant_message: Message
    warnings: list[str] = field(default_factory=list)
