from enum import Enum
from pydantic import BaseModel
from uuid import UUID
import json

from events.generation import (
    GenerationEvent,
    GenerationStarted,
    TextDelta,
    ToolStarted,
    ToolFinished,
    GenerationCompleted,
    GenerationCancelled,
    GenerationFailed,
)


class EventType(str, Enum):
    CONVERSATION = "conversation"
    MESSAGE = "message"
    TEXT = "text"
    TOOL_STARTED = "tool_started"
    TOOL_FINISHED = "tool_finished"
    DONE = "done"
    CANCELLED = "cancelled"
    ERROR = "error"


class ConversationEvent(BaseModel):
    conversation_id: UUID
    generation_id: UUID


class MessageEvent(BaseModel):
    message_id: UUID


class TextPayload(BaseModel):
    content: str


class ToolStartedPayload(BaseModel):
    id: str
    name: str
    arguments: dict


class ToolFinishedPayload(BaseModel):
    id: str
    name: str
    status: str
    content: str
    is_error: bool


class ErrorEvent(BaseModel):
    message: str


def sse_event(event: EventType, data: BaseModel | None = None):
    payload = data.model_dump(mode="json") if data else {}

    return (
        f"event: {event.value}\n"
        f"data: {json.dumps(payload)}\n\n"
    )


def to_sse(event: GenerationEvent) -> str:
    """Translate an application-level GenerationEvent into an SSE frame.

    The only place that knows both the generation layer and the wire layer.
    """
    if isinstance(event, GenerationStarted):
        return sse_event(
            EventType.CONVERSATION,
            ConversationEvent(
                conversation_id=event.conversation_id,
                generation_id=event.generation_id,
            ),
        )
    if isinstance(event, TextDelta):
        return sse_event(EventType.TEXT, TextPayload(content=event.text))
    if isinstance(event, ToolStarted):
        return sse_event(
            EventType.TOOL_STARTED,
            ToolStartedPayload(
                id=event.id,
                name=event.name,
                arguments=event.arguments,
            ),
        )
    if isinstance(event, ToolFinished):
        return sse_event(
            EventType.TOOL_FINISHED,
            ToolFinishedPayload(
                id=event.id,
                name=event.name,
                status=event.status,
                content=event.content,
                is_error=event.is_error,
            ),
        )
    if isinstance(event, GenerationCompleted):
        return sse_event(EventType.DONE)
    if isinstance(event, GenerationCancelled):
        return sse_event(EventType.CANCELLED)
    if isinstance(event, GenerationFailed):
        return sse_event(EventType.ERROR, ErrorEvent(message=event.message))

    raise TypeError(f"Unknown generation event: {type(event).__name__}")
