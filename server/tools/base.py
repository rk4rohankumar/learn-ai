from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolDefinition:
    """Metadata only — this is what the LLM eventually sees.

    Shape matches Anthropic's tool param exactly (name/description/input_schema),
    so the fake→native migration is near-free.
    """
    name: str
    description: str
    input_schema: dict


@dataclass
class ToolResult:
    """The business outcome of a tool. Answers: what did the tool tell me?

    success=False is a *successful execution* that reported a business failure
    (e.g. "repo not found"). It is NOT an infrastructure error — see ToolExecution.
    """
    success: bool
    content: str
    metadata: dict = field(default_factory=dict)


class Tool(ABC):
    definition: ToolDefinition

    @abstractmethod
    async def execute(self, arguments: dict) -> ToolResult:
        """Execute one capability. Validate business logic, not schema.

        Raise only for infrastructure failures (network down, etc.) — those
        become ToolExecution.status = FAILED. Business failures return
        ToolResult(success=False).
        """
        ...
