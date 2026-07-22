from pydantic import BaseModel
from uuid import UUID
class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str


class ChatResponse(BaseModel):
    conversation_id: UUID
    assistant_message: str