from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from services.conversation_service import conversation_service
from services.llm_service import llm_service
from services.generation_service import generation_service
from events.sse import sse_event, EventType, ConversationEvent, TextPayload, ErrorEvent
from events.llm import TextEvent, GenerationCompletedEvent
import config

from db import SessionLocal
from schemas import ChatRequest
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def stream_response(session, conversation, messages,generation):
    chunks = []
    stream_started = False

    try:
        #send conversation id and generation id first
        yield sse_event(
            EventType.CONVERSATION,
            ConversationEvent(
                conversation_id=conversation.id,
                generation_id=generation.id,
            ),
        )
        #stream internal llm events, translate to sse
        for event in llm_service.stream(messages):
            if isinstance(event, TextEvent):
                if not stream_started:
                    stream_started = True
                    generation_service.mark_streaming(generation)

                chunks.append(event.text)
                yield sse_event(
                    EventType.TEXT,
                    TextPayload(content=event.text),
                )
            elif isinstance(event, GenerationCompletedEvent):
                assistant_content = "".join(chunks)
                #saving assistant message
                assistant_message = conversation_service.save_message(
                    session=session,
                    conversation_id=conversation.id,
                    role="assistant",
                    content=assistant_content,
                )
                generation_service.mark_completed(
                    generation=generation,
                    assistant_message=assistant_message,
                    event=event,
                )
                session.commit()
                #send conversation end event
                yield sse_event(EventType.DONE)
    except Exception as e:
        session.rollback()
        yield sse_event(EventType.ERROR, ErrorEvent(message=str(e)))
        return
    finally:
        session.close()


@app.post("/chat")
def chat(req: ChatRequest):
    session = SessionLocal()

    try:
        conversation = conversation_service.get_or_create_conversation(
            session=session,
            conversation_id=req.conversation_id,
        )

        user_message = conversation_service.save_message(
            session=session,
            conversation_id=conversation.id,
            role="user",
            content=req.message,)
        
        generation = generation_service.create(
            session=session,
            user_message=user_message,
            provider=config.LLM_PROVIDER,
            model=config.LLM_PROVIDER_MODEL
        )
        
        messages = conversation_service.build_messages(
            session,
            conversation.id,
        )

    except Exception:
        session.rollback()
        session.close()
        raise
    
    return StreamingResponse(
            stream_response(
                session=session,
                conversation=conversation,
                messages=messages,
                generation=generation,
                ),
            media_type="text/event-stream",
            headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    },
        )