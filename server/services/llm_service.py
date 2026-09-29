from abc import ABC, abstractmethod
from typing import AsyncIterator

import asyncio

from anthropic import AsyncAnthropic
from anthropic.lib.streaming._types import TextEvent as AnthropicTextEvent

import config
from events.llm import (
    LLMEvent,
    TextEvent,
    ToolCallEvent,
    MessageStopEvent,
    ToolResultSubmission,
)
from services.prompt_builder import Prompt
from tools.base import ToolDefinition

client = AsyncAnthropic(
    api_key=config.ANTHROPIC_API_KEY,
)


class LLMSession(ABC):
    """A single provider conversation. Stateful and per-generation.

    Owns all provider message plumbing (tool_use / tool_result reconstruction)
    so the runner speaks only in LLM events. NEVER share across requests — the
    message history is mutable state.
    """

    @abstractmethod
    def stream(self) -> AsyncIterator[LLMEvent]:
        """Stream one turn: TextEvent*, ToolCallEvent*, then one MessageStopEvent."""
        ...

    @abstractmethod
    def submit_tool_results(self, results: list[ToolResultSubmission]) -> None:
        """Append results of the previous turn's tool calls before the next stream().

        INVARIANT: every ToolResultSubmission must correspond to a ToolCallEvent
        emitted by the immediately preceding stream() call — one result per call,
        each referencing its tool_use_id. Anthropic requires exactly this.
        """
        ...


class AnthropicLLMSession(LLMSession):
    def __init__(
        self,
        prompt: Prompt,
        tool_definitions: list[ToolDefinition],
    ) -> None:
        # translate provider-neutral PromptMessage -> Anthropic wire shape;
        # this class is the only place that speaks Anthropic
        self._system = prompt.system
        self._messages: list[dict] = [
            {"role": m.role, "content": m.content} for m in prompt.messages
        ]
        self._tools = [
            {
                "name": d.name,
                "description": d.description,
                "input_schema": d.input_schema,
            }
            for d in tool_definitions
        ]

    async def stream(self) -> AsyncIterator[LLMEvent]:
        kwargs = dict(
            model=config.LLM_PROVIDER_MODEL,
            max_tokens=1024,
            messages=self._messages,
        )
        if self._system:
            kwargs["system"] = self._system
        if self._tools:
            kwargs["tools"] = self._tools

        async with client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if isinstance(event, AnthropicTextEvent):
                    yield TextEvent(text=event.text)
            final = await stream.get_final_message()

        # record the assistant turn so a follow-up call has full history
        self._messages.append(
            {"role": "assistant", "content": final.content}
        )

        for block in final.content:
            if block.type == "tool_use":
                yield ToolCallEvent(
                    id=block.id,
                    name=block.name,
                    arguments=block.input,
                )

        yield MessageStopEvent(
            stop_reason=final.stop_reason,
            usage=final.usage,
        )

    def submit_tool_results(self, results: list[ToolResultSubmission]) -> None:
        self._messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": r.tool_use_id,
                        "content": r.content,
                        "is_error": r.is_error,
                    }
                    for r in results
                ],
            }
        )


class MockLLMSession(LLMSession):
    """Fakes the tool-calling protocol without spending tokens.

    Turn 1: request the weather tool. Turn 2 (after results): stream a reply
    that echoes the tool result. Exercises the exact runner dispatch path.
    """

    def __init__(
        self,
        prompt: Prompt,
        tool_definitions: list[ToolDefinition],
    ) -> None:
        self._prompt = prompt
        self._results: list[ToolResultSubmission] | None = None
        self._turn = 0

    async def stream(self) -> AsyncIterator[LLMEvent]:
        self._turn += 1

        if self._results is None:
            # first turn — ask for a tool
            await asyncio.sleep(0.3)
            yield ToolCallEvent(
                id="toolu_mock_1",
                name="weather",
                arguments={"city": "Delhi"},
            )
            yield MessageStopEvent(stop_reason="tool_use", usage=None)
            return

        # subsequent turn — answer using the tool results
        tool_text = self._results[0].content if self._results else ""
        for word in ["Based ", "on ", "the ", "tool: ", tool_text]:
            await asyncio.sleep(0.2)
            yield TextEvent(text=word)
        yield MessageStopEvent(stop_reason="end_turn", usage=None)

    def submit_tool_results(self, results: list[ToolResultSubmission]) -> None:
        self._results = results


class LLMService:
    """Factory for per-generation sessions. Stateless — safe as a singleton."""

    def create_session(
        self,
        prompt: Prompt,
        tool_definitions: list[ToolDefinition],
    ) -> LLMSession:
        return AnthropicLLMSession(prompt, tool_definitions)

    def create_mock_session(
        self,
        prompt: Prompt,
        tool_definitions: list[ToolDefinition],
    ) -> LLMSession:
        return MockLLMSession(prompt, tool_definitions)


llm_service = LLMService()
