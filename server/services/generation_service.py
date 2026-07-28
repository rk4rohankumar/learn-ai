from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from models import (
    Generation,
    GenerationStatus,
    Message,
    TERMINAL_GENERATION_STATUSES,
)


class GenerationService:

    def create(
        self,
        session: Session,
        user_message: Message,
        provider: str,
        model: str,
    ) -> Generation:
        generation = Generation(
            user_message_id=user_message.id,
            provider=provider,
            model=model,
            status=GenerationStatus.CREATED,
        )

        session.add(generation)
        session.flush()

        return generation

    def mark_streaming(self, generation: Generation) -> None:
        if generation.status != GenerationStatus.CREATED:
            raise RuntimeError(
                f"Cannot mark generation as STREAMING from {generation.status}"
            )

        generation.status = GenerationStatus.STREAMING
        generation.first_token_at = datetime.now(timezone.utc)

    def complete(
        self,
        generation: Generation,
        assistant_message: Message,
        stop_reason: str | None,
        usage: Any = None,
    ) -> None:
        # allow CREATED too: an empty response completes without a first token
        if generation.status not in (
            GenerationStatus.CREATED,
            GenerationStatus.STREAMING,
        ):
            raise RuntimeError(
                f"Cannot mark generation as COMPLETED from {generation.status}"
            )

        generation.assistant_message_id = assistant_message.id
        generation.status = GenerationStatus.COMPLETED
        generation.completed_at = datetime.now(timezone.utc)
        generation.stop_reason = stop_reason

        if usage:
            generation.input_tokens = usage.input_tokens
            generation.output_tokens = usage.output_tokens

    def fail(self, generation: Generation, message: str) -> None:
        # terminal setter — must not raise; used on the error path
        generation.status = GenerationStatus.FAILED
        generation.error = message
        generation.completed_at = datetime.now(timezone.utc)

    def cancel(
        self,
        generation: Generation,
        assistant_message: Message | None = None,
    ) -> None:
        # terminal setter — must not raise. assistant_message links the
        # partial reply, if any text was produced before the stop.
        if assistant_message is not None:
            generation.assistant_message_id = assistant_message.id
        generation.status = GenerationStatus.CANCELLED
        generation.completed_at = datetime.now(timezone.utc)

    def request_cancel(
        self,
        session: Session,
        generation_id: UUID,
    ) -> Generation | None:
        """Record a cancellation REQUEST. Never touches `status` — the runner
        is the single writer of status; this endpoint-side path only stamps
        cancel_requested_at. Idempotent: the first timestamp wins.

        Returns the generation (caller decides 202 vs 200 by its status),
        or None if it doesn't exist.
        """
        generation = session.get(Generation, generation_id)
        if generation is None:
            return None
        if generation.status in TERMINAL_GENERATION_STATUSES:
            return generation
        if generation.cancel_requested_at is None:
            generation.cancel_requested_at = datetime.now(timezone.utc)
        return generation

    def is_cancel_requested(
        self,
        session: Session,
        generation_id: UUID,
    ) -> bool:
        """Targeted single-column poll, NOT an identity-map read.

        generation.cancel_requested_at on the ORM object would return the
        stale loaded value, and session.refresh() would clobber pending
        uncommitted mutations (STREAMING). A column query does neither:
        autoflush=False keeps pending state unflushed, and READ COMMITTED
        lets each new statement see the cancel endpoint's committed write.
        """
        return (
            session.query(Generation.cancel_requested_at)
            .filter(Generation.id == generation_id)
            .scalar()
        ) is not None


generation_service = GenerationService()
