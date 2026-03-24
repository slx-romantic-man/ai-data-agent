"""
Data Analysis Tool - Performs data analysis and generates insights.
"""
from typing import Any, Dict, Optional, List

from app.agent.tools.base_tool import BaseTool
from app.models.permission import PermissionContext
from app.models.tool import ToolResult
from app.agent.core.data_analyzer import DataAnalyzer


class AnalysisTool(BaseTool):
    """
    Tool for performing data analysis.
    """

    def __init__(self):
        self._analyzer = DataAnalyzer()

    @property
    def name(self) -> str:
        return "data_analysis"

    @property
    def description(self) -> str:
        return "Analyze data to generate insights, trends, and recommendations."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "description": "Data rows to analyze",
                    "items": {"type": "object"},
                },
                "analysis_type": {
                    "type": "string",
                    "description": "Type of analysis: summary, trend, comparison, anomaly",
                    "enum": ["summary", "trend", "comparison", "anomaly"],
                    "default": "summary",
                },
                "dimensions": {
                    "type": "array",
                    "description": "Dimensions for analysis",
                    "items": {"type": "string"},
                },
                "metrics": {
                    "type": "array",
                    "description": "Metrics to analyze",
                    "items": {"type": "string"},
                },
                "user_query": {
                    "type": "string",
                    "description": "Original user query for context",
                },
            },
            "required": ["data"],
        }

    async def execute(
        self,
        params: Dict[str, Any],
        permission: PermissionContext,
    ) -> ToolResult:
        """
        Execute data analysis.

        Args:
            params: Dict with 'data', 'analysis_type', 'dimensions', 'metrics'
            permission: Permission context

        Returns:
            ToolResult with analysis results
        """
        try:
            self.validate_params(params)

            data = params.get("data", [])
            analysis_type = params.get("analysis_type", "summary")
            dimensions = params.get("dimensions", [])
            metrics = params.get("metrics", [])
            user_query = params.get("user_query", "")

            if not data:
                return self._success(
                    data={"analysis": "无数据可供分析", "insights": []},
                )

            # Perform analysis
            result = await self._analyzer.analyze(
                data=data,
                user_query=user_query,
                analysis_type=analysis_type,
                dimensions=dimensions,
                metrics=metrics,
            )

            # Add statistical summary
            result["statistics"] = self._calculate_statistics(data, metrics)

            return self._success(
                data=result,
                metadata={
                    "analysis_type": analysis_type,
                    "data_rows": len(data),
                    "dimensions": dimensions,
                    "metrics": metrics,
                },
            )

        except Exception as e:
            return self._error(f"Analysis failed: {str(e)}")

    def _calculate_statistics(
        self,
        data: List[Dict[str, Any]],
        metrics: List[str],
    ) -> Dict[str, Any]:
        """Calculate statistical summary for metrics."""
        statistics = {}

        for metric in metrics:
            values = [row.get(metric) for row in data if row.get(metric) is not None]
            if not values:
                continue

            # Check if numeric
            if all(isinstance(v, (int, float)) for v in values):
                statistics[metric] = {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }

        return statistics


# Global analysis tool instance
_analysis_tool: Optional[AnalysisTool] = None


def get_analysis_tool() -> AnalysisTool:
    """Get analysis tool instance."""
    global _analysis_tool
    if _analysis_tool is None:
        _analysis_tool = AnalysisTool()
    return _analysis_tool