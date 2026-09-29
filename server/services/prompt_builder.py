from dataclasses import dataclass

import config
from models import Message


@dataclass(frozen=True)
class PromptMessage:
    """Provider-neutral message. LLMSession translates this into the
    provider's wire shape — PromptBuilder never speaks Anthropic."""
    role: str  # "user" | "assistant"
    content: str


@dataclass(frozen=True)
class Prompt:
    """Everything the model will see. Grows fields (truncated,
    estimated_tokens, ...) without changing any signatures."""
    system: str | None
    messages: list[PromptMessage]


class PromptBuilder:
    """Decides exactly what the model sees.

    Pure policy over already-persisted state: the runner persists the user
    message FIRST, then fetches history, then builds. Invariant: the prompt
    is always reconstructible from the database (replay/regeneration safe).

    INVARIANT (truncation, later): only user/assistant TEXT is persisted —
    tool_use/tool_result blocks live solely inside LLMSession's per-generation
    memory. History is therefore clean alternating text and truncation can
    never split a tool_use from its tool_result. If tool traces ever get
    persisted, that assumption breaks and truncation must become pair-aware.
    """

    def build(
        self,
        history: list[Message],
        budget: int | None = None,
    ) -> Prompt:
        # v1: system prompt + full history. `budget` is the seam where
        # truncation lands next iteration.
        return Prompt(
            system=config.SYSTEM_PROMPT,
            messages=[
                PromptMessage(role=m.role, content=m.content) for m in history
            ],
        )


prompt_builder = PromptBuilder()
