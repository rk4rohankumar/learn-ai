from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import Generation, GenerationStatus, Message


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

    def cancel(self, generation: Generation) -> None:
        generation.status = GenerationStatus.CANCELLED
        generation.completed_at = datetime.now(timezone.utc)


generation_service = GenerationService()
