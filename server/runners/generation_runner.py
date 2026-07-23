from typing import AsyncIterator

from sqlalchemy.orm import Session

import config
from schemas import ChatRequest
from services.conversation_service import conversation_service
from services.generation_service import generation_service
from services.llm_service import llm_service
from events.llm import TextEvent, GenerationCompletedEvent
from events.generation import (
    GenerationEvent,
    GenerationStarted,
    TextDelta,
    GenerationCompleted,
    GenerationFailed,
)


class GenerationRunner:
    """Executes one Generation from start to finish.

    Owns the workflow and the business transaction. Coordinates services;
    knows nothing about HTTP or SSE. Yields application-level GenerationEvents.
    """

    async def run(
        self,
        session: Session,
        req: ChatRequest,
    ) -> AsyncIterator[GenerationEvent]:
        generation = None
        try:
            # --- setup: everything a real generation needs to exist ---
            conversation = conversation_service.get_or_create_conversation(
                session=session,
                conversation_id=req.conversation_id,
            )
            user_message = conversation_service.save_message(
                session=session,
                conversation_id=conversation.id,
                role="user",
                content=req.message,
            )
            generation = generation_service.create(
                session=session,
                user_message=user_message,
                provider=config.LLM_PROVIDER,
                model=config.LLM_PROVIDER_MODEL,
            )
            conversation_id = conversation.id
            generation_id = generation.id

            # commit setup so the generation truly exists before we announce it,
            # and so a failed/cancelled generation survives a later rollback.
            session.commit()

            yield GenerationStarted(
                conversation_id=conversation_id,
                generation_id=generation_id,
            )

            messages = conversation_service.build_messages(
                session,
                conversation_id,
            )

            # --- generation lifecycle ---
            chunks: list[str] = []
            started = False

            async for event in llm_service.stream(messages):
                if isinstance(event, TextEvent):
                    if not started:
                        started = True
                        generation_service.mark_streaming(generation)

                    chunks.append(event.text)
                    yield TextDelta(text=event.text)

                elif isinstance(event, GenerationCompletedEvent):
                    assistant_message = conversation_service.save_message(
                        session=session,
                        conversation_id=conversation_id,
                        role="assistant",
                        content="".join(chunks),
                    )
                    generation_service.complete(
                        generation=generation,
                        assistant_message=assistant_message,
                        event=event,
                    )
                    session.commit()

                    yield GenerationCompleted(
                        stop_reason=event.stop_reason,
                        usage=event.usage,
                    )

        except Exception as e:
            session.rollback()
            # persist the failure if we got far enough to have a generation row
            if generation is not None:
                try:
                    generation_service.fail(generation, str(e))
                    session.commit()
                except Exception:
                    session.rollback()
            yield GenerationFailed(message=str(e))

        finally:
            session.close()


generation_runner = GenerationRunner()
