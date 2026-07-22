from enum import Enum
from pydantic import BaseModel
from uuid import UUID
import json

class EventType(str, Enum):
    CONVERSATION = "conversation"
    MESSAGE = "message"
    TEXT = "text"
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


class ErrorEvent(BaseModel):
    message: str


def sse_event(event: EventType, data: BaseModel | None = None):
    payload = data.model_dump(mode="json") if data else {}

    return (
        f"event: {event.value}\n"
        f"data: {json.dumps(payload)}\n\n"
    )
