from enum import StrEnum


class MessageRole(StrEnum):
    """docs/52 §6. Only conversational turns are persisted - the system
    prompt is assembled fresh per request (`chat_prompt_builder.py`),
    never stored as a message row."""

    USER = "user"
    ASSISTANT = "assistant"
