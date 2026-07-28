from datetime import datetime, timezone

from tools.base import Tool, ToolDefinition
from tools.execution import ToolExecution, ToolExecutionStatus


class ToolRegistry:
    """Owns every tool implementation and executes the correct one.

    execute() returns a ToolExecution (never a raw result) so the signature
    stays stable while the execution object grows new concerns.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.definition.name] = tool

    def list_definitions(self) -> list[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    async def execute(self, name: str, arguments: dict) -> ToolExecution:
        execution = ToolExecution(tool_name=name, arguments=arguments)

        tool = self._tools.get(name)
        if tool is None:
            execution.status = ToolExecutionStatus.FAILED
            execution.error_message = f"Unknown tool: {name}"
            execution.completed_at = datetime.now(timezone.utc)
            return execution

        execution.status = ToolExecutionStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        try:
            execution.result = await tool.execute(arguments)
            execution.status = ToolExecutionStatus.COMPLETED
        except Exception as e:  # infrastructure failure, not a business one
            execution.error_message = f"{type(e).__name__}: {e}"
            execution.status = ToolExecutionStatus.FAILED

        execution.completed_at = datetime.now(timezone.utc)
        return execution


tool_registry = ToolRegistry()
