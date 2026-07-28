from typing import AsyncIterator, Callable

from sqlalchemy.orm import Session

import config
from schemas import ChatRequest
from services.conversation_service import conversation_service
from services.generation_service import generation_service
from services.llm_service import llm_service, LLMSession
from tools.base import ToolDefinition
from tools.registry import tool_registry
from tools.execution import ToolExecutionStatus
from events.llm import (
    TextEvent,
    ToolCallEvent,
    MessageStopEvent,
    ToolResultSubmission,
)
from events.generation import (
    GenerationEvent,
    GenerationStarted,
    TextDelta,
    ToolStarted,
    ToolFinished,
    GenerationCompleted,
    GenerationFailed,
)


class GenerationRunner:
    """Executes one Generation from start to finish.

    Owns the workflow and the business transaction. Coordinates services and
    the tool registry; knows nothing about HTTP, SSE, or provider message
    formats. Yields application-level GenerationEvents.
    """

    # a factory (messages, tool_definitions) -> LLMSession. Injected so the
    # runner never decides Anthropic-vs-mock — the caller supplies the session.
    SessionFactory = Callable[[list[dict], list[ToolDefinition]], LLMSession]

    def __init__(
        self,
        session_factory: "GenerationRunner.SessionFactory",
        max_iterations: int = 10,
    ) -> None:
        self._create_session = session_factory
        # safety rail: cap the LLM<->tool loop so a runaway model can't spend
        # unbounded tokens. Not speculative — a NOT NULL for the loop.
        self.max_iterations = max_iterations

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
            # and so a failed generation survives a later rollback.
            session.commit()

            yield GenerationStarted(
                conversation_id=conversation_id,
                generation_id=generation_id,
            )

            messages = conversation_service.build_messages(
                session,
                conversation_id,
            )
            llm = self._create_session(
                messages,
                tool_registry.list_definitions(),
            )

            # --- generation lifecycle: loop LLM <-> tools until done ---
            chunks: list[str] = []
            started = False
            stop_reason: str | None = None
            usage = None
            completed = False

            for _ in range(self.max_iterations):
                tool_calls: list[ToolCallEvent] = []

                async for event in llm.stream():
                    if isinstance(event, TextEvent):
                        if not started:
                            started = True
                            generation_service.mark_streaming(generation)
                        chunks.append(event.text)
                        yield TextDelta(text=event.text)
                    elif isinstance(event, ToolCallEvent):
                        tool_calls.append(event)
                    elif isinstance(event, MessageStopEvent):
                        stop_reason = event.stop_reason
                        usage = event.usage

                if not tool_calls:
                    completed = True
                    break

                # execute every tool call from this turn, batch results back
                submissions: list[ToolResultSubmission] = []
                for call in tool_calls:
                    yield ToolStarted(
                        id=call.id,
                        name=call.name,
                        arguments=call.arguments,
                    )

                    execution = await tool_registry.execute(
                        call.name,
                        call.arguments,
                    )

                    if (
                        execution.status == ToolExecutionStatus.COMPLETED
                        and execution.result is not None
                    ):
                        content = execution.result.content
                        is_error = not execution.result.success
                    else:
                        content = execution.error_message or "Tool execution failed"
                        is_error = True

                    submissions.append(
                        ToolResultSubmission(
                            tool_use_id=call.id,
                            content=content,
                            is_error=is_error,
                        )
                    )

                    yield ToolFinished(
                        id=call.id,
                        name=call.name,
                        status=execution.status.value,
                        content=content,
                        is_error=is_error,
                    )

                llm.submit_tool_results(submissions)

            if not completed:
                raise RuntimeError(
                    f"Generation exceeded max_iterations ({self.max_iterations})"
                )

            # --- persist completion ---
            assistant_message = conversation_service.save_message(
                session=session,
                conversation_id=conversation_id,
                role="assistant",
                content="".join(chunks),
            )
            generation_service.complete(
                generation=generation,
                assistant_message=assistant_message,
                stop_reason=stop_reason,
                usage=usage,
            )
            session.commit()

            yield GenerationCompleted(stop_reason=stop_reason, usage=usage)

        except Exception as e:
            session.rollback()
            if generation is not None:
                try:
                    generation_service.fail(generation, str(e))
                    session.commit()
                except Exception:
                    session.rollback()
            yield GenerationFailed(message=str(e))

        finally:
            session.close()


# composition root: wire the real Anthropic session factory as the default
generation_runner = GenerationRunner(session_factory=llm_service.create_session)
