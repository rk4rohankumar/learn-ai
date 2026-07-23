from anthropic import AsyncAnthropic
from anthropic.lib.streaming._types import (
    TextEvent as AnthropicTextEvent,
    ParsedMessageStopEvent,
)
from events.llm import TextEvent, GenerationCompletedEvent
import asyncio
import config

client = AsyncAnthropic(
    api_key=config.ANTHROPIC_API_KEY,
)


class LLMService:

    async def stream_mock(self, messages: list[dict]):
        for word in ["Hello", " ", "World", "!"]:
            await asyncio.sleep(1)
            yield TextEvent(text=word)

        yield GenerationCompletedEvent(
            stop_reason="end_turn",
            usage=None,
        )

    async def stream(self, messages: list[dict]):
        async with client.messages.stream(
            model=config.LLM_PROVIDER_MODEL,
            max_tokens=1024,
            messages=messages,
        ) as stream:
            async for event in stream:
                if isinstance(event, AnthropicTextEvent):
                    yield TextEvent(text=event.text)
                elif isinstance(event, ParsedMessageStopEvent):
                    yield GenerationCompletedEvent(
                        stop_reason=event.message.stop_reason,
                        usage=event.message.usage,
                    )
                else:
                    continue


llm_service = LLMService()
