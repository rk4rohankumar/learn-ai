from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from db import SessionLocal
from models import Conversation, TERMINAL_GENERATION_STATUSES
from schemas import ChatRequest, ConversationSummary, MessageOut
from services.conversation_service import conversation_service
from services.generation_service import generation_service
from runners.generation_runner import generation_runner
from events.sse import to_sse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat")
async def chat(req: ChatRequest):
    session = SessionLocal()

    async def event_stream():
        async for event in generation_runner.run(session, req):
            yield to_sse(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/conversations", response_model=list[ConversationSummary])
def list_conversations():
    session = SessionLocal()
    try:
        # no user concept yet — everything comes back; auth scopes this later
        return conversation_service.list_conversations(session)
    finally:
        session.close()


@app.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut],
)
def get_conversation_messages(conversation_id: UUID):
    session = SessionLocal()
    try:
        if session.get(Conversation, conversation_id) is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation_service.get_messages(session, conversation_id)
    finally:
        session.close()


@app.post("/generations/{generation_id}/cancel", status_code=202)
def cancel_generation(generation_id: UUID):
    session = SessionLocal()
    try:
        generation = generation_service.request_cancel(session, generation_id)
        if generation is None:
            raise HTTPException(status_code=404, detail="Generation not found")

        session.commit()

        body = {
            "generation_id": str(generation.id),
            "status": generation.status.value,
            "cancel_requested_at": (
                generation.cancel_requested_at.isoformat()
                if generation.cancel_requested_at
                else None
            ),
        }

        # already terminal: nothing to cancel — report the fact, not a promise
        if generation.status in TERMINAL_GENERATION_STATUSES:
            return JSONResponse(status_code=200, content=body)

        # 202: the request is accepted; the runner will stop best-effort
        return body
    finally:
        session.close()
