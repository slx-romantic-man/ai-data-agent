"""
Tool Router - Routes tool requests to appropriate tool implementations.
"""
from typing import Dict, Optional, Type

from app.agent.tools.base_tool import BaseTool
from app.agent.tools.sql_query_tool import SQLQueryTool, get_sql_query_tool
from app.agent.tools.api_fetch_tool import APIFetchTool, get_api_fetch_tool
from app.agent.tools.analysis_tool import AnalysisTool, get_analysis_tool
from app.agent.tools.export_tool import ExportTool, get_export_tool


class ToolRouter:
    """
    Routes tool requests to appropriate tool implementations.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize all tools."""
        if self._initialized:
            return

        # Register default tools
        self._tools["sql_query"] = await get_sql_query_tool()
        self._tools["api_fetch"] = get_api_fetch_tool()
        self._tools["data_analysis"] = get_analysis_tool()
        self._tools["export_excel"] = get_export_tool()

        self._initialized = True

    def register_tool(self, tool: BaseTool):
        """Register a new tool."""
        self._tools[tool.name] = tool

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get tool by name."""
        return self._tools.get(tool_name)

    def list_tools(self) -> Dict[str, str]:
        """List all available tools with descriptions."""
        return {
            name: tool.description
            for name, tool in self._tools.items()
        }

    def get_tool_schemas(self) -> list:
        """Get JSON schemas for all tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]


# Global tool router instance
_tool_router: Optional[ToolRouter] = None


async def get_tool_router() -> ToolRouter:
    """Get tool router instance."""
    global _tool_router
    if _tool_router is None:
        _tool_router = ToolRouter()
        await _tool_router.initialize()
    return _tool_router