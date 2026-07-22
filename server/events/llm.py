from dataclasses import dataclass
from typing import Any


@dataclass
class LLMEvent:
    """Base class for all internal LLM events."""
    pass


@dataclass
class TextEvent(LLMEvent):
    text: str


@dataclass
class GenerationCompletedEvent(LLMEvent):
    stop_reason: str | None
    usage: Any


@dataclass
class GenerationErrorEvent(LLMEvent):
    message: str
