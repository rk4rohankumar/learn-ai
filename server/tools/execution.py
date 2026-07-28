from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from tools.base import ToolResult


class ToolExecutionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolExecution:
    """Runtime object — whether the execution infrastructure succeeded.

    Answers: did my code successfully execute the tool? Wraps a ToolResult
    (the business outcome). Not persisted in v1; grows to carry duration,
    cancellation, retries, metrics without changing the registry signature.
    """
    tool_name: str
    arguments: dict
    id: UUID = field(default_factory=uuid4)
    status: ToolExecutionStatus = ToolExecutionStatus.CREATED
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: ToolResult | None = None
    # a string, not an Exception: serializable, log-friendly, survives a
    # process boundary and future persistence. The registry owns the conversion.
    error_message: str | None = None
