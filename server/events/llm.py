from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMEvent:
    """Base class for provider-layer events — what the provider emitted."""
    pass


@dataclass
class TextEvent(LLMEvent):
    text: str


@dataclass
class ToolCallEvent(LLMEvent):
    # id = provider tool_use_id; every tool_result must reference it, so the
    # runner threads it back through the session. Mock generates a fake one.
    id: str
    name: str
    arguments: dict


@dataclass
class MessageStopEvent(LLMEvent):
    """The model's turn ended. NOT necessarily the generation.

    stop_reason == "tool_use" means the model paused to call tools and the
    runner must continue; anything else ("end_turn", ...) ends the generation.
    """
    stop_reason: str | None
    usage: Any


@dataclass
class GenerationErrorEvent(LLMEvent):
    message: str


@dataclass
class ToolResultSubmission:
    """Runner -> session: the result of one tool_use, sent back to the provider.

    Maps directly to an Anthropic tool_result block.
    """
    tool_use_id: str
    content: str
    is_error: bool = False
