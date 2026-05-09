"""
Base tool class for all Agent tools.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.models.permission import PermissionContext
from app.models.tool import ToolResult, ToolStatus


class BaseTool(ABC):
    """
    Abstract base class for all Agent tools.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name identifier."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM understanding."""
        pass

    @property
    def input_schema(self) -> Dict[str, Any]:
        """JSON schema for tool input parameters."""
        return {
            "type": "object",
            "properties": {},
        }

    @abstractmethod
    async def execute(
        self,
        params: Dict[str, Any],
        permission: PermissionContext,
    ) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            params: Tool input parameters
            permission: Permission context for the executing user

        Returns:
            ToolResult with execution outcome
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate input parameters against schema.

        Args:
            params: Input parameters to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        required_props = self.input_schema.get("required", [])
        for prop in required_props:
            if prop not in params:
                raise ValueError(f"Missing required parameter: {prop}")
        return True

    def _success(self, data: Any, metadata: Optional[Dict] = None) -> ToolResult:
        """Create a successful tool result."""
        return ToolResult(
            tool_name=self.name,
            status=ToolStatus.SUCCESS,
            data=data,
            metadata=metadata or {},
        )

    def _error(self, error_message: str, metadata: Optional[Dict] = None) -> ToolResult:
        """Create an error tool result."""
        return ToolResult(
            tool_name=self.name,
            status=ToolStatus.FAILED,
            error=error_message,
            metadata=metadata or {},
        )