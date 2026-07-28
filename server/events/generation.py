from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass
class GenerationEvent:
    """Base class for application-level generation events.

    These describe what happened in *our* application — one layer above the
    provider events in events/llm.py, one layer below the SSE wire format in
    events/sse.py. None of the three layers knows about the others.
    """
    pass


@dataclass
class GenerationStarted(GenerationEvent):
    conversation_id: UUID
    generation_id: UUID


@dataclass
class TextDelta(GenerationEvent):
    text: str


@dataclass
class ToolStarted(GenerationEvent):
    id: str
    name: str
    arguments: dict


@dataclass
class ToolFinished(GenerationEvent):
    id: str
    name: str
    status: str
    content: str
    is_error: bool


@dataclass
class GenerationCompleted(GenerationEvent):
    stop_reason: str | None
    usage: Any


@dataclass
class GenerationFailed(GenerationEvent):
    message: str


@dataclass
class GenerationCancelled(GenerationEvent):
    pass
