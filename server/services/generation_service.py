from datetime import datetime, timezone

from sqlalchemy.orm import Session

from events.llm import GenerationCompletedEvent
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

    def mark_completed(
        self,
        generation: Generation,
        assistant_message: Message,
        event: GenerationCompletedEvent,
    ) -> None:
        if generation.status != GenerationStatus.STREAMING:
            raise RuntimeError(
                f"Cannot mark generation as COMPLETED from {generation.status}"
            )

        generation.assistant_message_id = assistant_message.id
        generation.status = GenerationStatus.COMPLETED
        generation.completed_at = datetime.now(timezone.utc)
        generation.stop_reason = event.stop_reason

        if event.usage:
            generation.input_tokens = event.usage.input_tokens
            generation.output_tokens = event.usage.output_tokens


generation_service = GenerationService()
