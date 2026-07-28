import asyncio
import logging
import time
from typing import AsyncIterator, Callable
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

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
    GenerationCancelled,
    GenerationFailed,
)


class _CancelPoller:
    """Throttled poll of Generation.cancel_requested_at.

    check() hits the DB at most once per `interval` seconds; force=True
    bypasses the throttle (used at cheap, rare boundaries: turn start,
    per tool, final pre-complete check). A positive answer is cached —
    cancellation never un-happens.
    """

    def __init__(
        self,
        session: Session,
        generation_id: UUID,
        interval: float,
    ) -> None:
        self._session = session
        self._generation_id = generation_id
        self._interval = interval
        self._last_check = 0.0
        self._cancelled = False

    def check(self, force: bool = False) -> bool:
        if self._cancelled:
            return True
        now = time.monotonic()
        if not force and (now - self._last_check) < self._interval:
            return False
        self._last_check = now
        self._cancelled = generation_service.is_cancel_requested(
            self._session,
            self._generation_id,
        )
        return self._cancelled


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
        cancel_poll_interval: float = 0.5,
    ) -> None:
        self._create_session = session_factory
        # safety rail: cap the LLM<->tool loop so a runaway model can't spend
        # unbounded tokens. Not speculative — a NOT NULL for the loop.
        self.max_iterations = max_iterations
        self.cancel_poll_interval = cancel_poll_interval

    async def run(
        self,
        session: Session,
        req: ChatRequest,
    ) -> AsyncIterator[GenerationEvent]:
        generation = None
        # hoisted above try: the disconnect arm reads them, and a disconnect
        # can land on the very first yield, before the loop body ever ran.
        chunks: list[str] = []
        conversation_id = None

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
            llm = self._create_session(
                messages,
                tool_registry.list_definitions(),
            )
            poller = _CancelPoller(
                session,
                generation_id,
                self.cancel_poll_interval,
            )

            # --- generation lifecycle: loop LLM <-> tools until done ---
            started = False
            stop_reason: str | None = None
            usage = None
            completed = False
            cancelled = False

            for _ in range(self.max_iterations):
                # turn boundary — cheap and rare, so bypass the throttle
                if poller.check(force=True):
                    cancelled = True
                    break

                tool_calls: list[ToolCallEvent] = []

                async for event in llm.stream():
                    if isinstance(event, TextEvent):
                        if not started:
                            started = True
                            generation_service.mark_streaming(generation)
                        chunks.append(event.text)
                        yield TextDelta(text=event.text)
                        # mid-stream — throttled; breaking closes the
                        # provider stream via the generator's aclose
                        if poller.check():
                            cancelled = True
                            break
                    elif isinstance(event, ToolCallEvent):
                        tool_calls.append(event)
                    elif isinstance(event, MessageStopEvent):
                        stop_reason = event.stop_reason
                        usage = event.usage

                if cancelled:
                    break

                if not tool_calls:
                    completed = True
                    break

                # execute every tool call from this turn, batch results back
                submissions: list[ToolResultSubmission] = []
                for call in tool_calls:
                    if poller.check(force=True):
                        cancelled = True
                        break

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

                if cancelled:
                    break

                llm.submit_tool_results(submissions)

            if not cancelled and not completed:
                raise RuntimeError(
                    f"Generation exceeded max_iterations ({self.max_iterations})"
                )

            if not cancelled:
                # final check narrows the cancel-vs-complete race window;
                # a cancel that arrives after this legitimately loses.
                cancelled = poller.check(force=True)

            if cancelled:
                assistant_message = None
                if chunks:
                    # invariant: a persisted assistant message must be
                    # non-empty — an empty one corrupts future context.
                    assistant_message = conversation_service.save_message(
                        session=session,
                        conversation_id=conversation_id,
                        role="assistant",
                        content="".join(chunks),
                    )
                generation_service.cancel(generation, assistant_message)
                session.commit()
                yield GenerationCancelled()
                return

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

        except (asyncio.CancelledError, GeneratorExit):
            # implicit termination: client disconnected (tab close, network
            # drop) — the response task is cancelled at our current yield.
            # Same terminal path as explicit cancel, but: no yield (the
            # generator is closing) and ALWAYS re-raise (asyncio contract).
            session.rollback()
            if generation is not None:
                try:
                    assistant_message = None
                    if chunks:
                        assistant_message = conversation_service.save_message(
                            session=session,
                            conversation_id=conversation_id,
                            role="assistant",
                            content="".join(chunks),
                        )
                    generation_service.cancel(generation, assistant_message)
                    session.commit()
                except Exception:
                    session.rollback()
            raise

        except HTTPException as e:
            # expected, user-facing errors (e.g. 404 conversation not found) —
            # safe to forward the detail. NOTE: services raising HTTPException
            # is a layer leak; a domain exception should replace this later.
            session.rollback()
            if generation is not None:
                try:
                    generation_service.fail(generation, str(e.detail))
                    session.commit()
                except Exception:
                    session.rollback()
            yield GenerationFailed(message=str(e.detail))

        except Exception as e:
            # unexpected errors: full detail server-side (log + generation.error),
            # generic message to the client — raw exception text can leak
            # connection strings, keys, and paths.
            logger.exception("generation failed")
            session.rollback()
            if generation is not None:
                try:
                    generation_service.fail(generation, str(e))
                    session.commit()
                except Exception:
                    session.rollback()
            yield GenerationFailed(message="Internal error during generation")

        finally:
            session.close()


# composition root: wire the real Anthropic session factory as the default
generation_runner = GenerationRunner(session_factory=llm_service.create_session)
