"""
Query planner module.
Plans the execution steps for processing user queries.
"""
from typing import List, Optional, Dict, Any
from app.models.chat import IntentType, IntentResult, QueryPlan
from app.models.tool import ToolStep


class QueryPlanner:
    """
    Plans query execution steps based on intent analysis.
    """

    def __init__(self):
        # Define planning strategies for different intent types
        self._strategies = {
            IntentType.DATA_DETAIL: self._plan_detail_query,
            IntentType.DATA_STATISTIC: self._plan_statistic_query,
            IntentType.DATA_ANALYSIS: self._plan_analysis_query,
            IntentType.DATA_EXPORT: self._plan_export_query,
            IntentType.API_QUERY: self._plan_api_query,
        }

    async def plan(
        self,
        intent: IntentResult,
        user_context: Dict[str, Any],
        table_hints: Optional[List[str]] = None,
    ) -> QueryPlan:
        """
        Create execution plan for the query.

        Args:
            intent: Recognized intent
            user_context: User context with permissions
            table_hints: Optional hints about which tables to use

        Returns:
            QueryPlan with execution steps
        """
        strategy = self._strategies.get(intent.intent_type, self._plan_default)
        return await strategy(intent, user_context, table_hints)

    async def _plan_detail_query(
        self,
        intent: IntentResult,
        user_context: Dict[str, Any],
        table_hints: Optional[List[str]] = None,
    ) -> QueryPlan:
        """Plan for data detail queries."""
        steps = []

        # Step 1: Generate SQL query
        steps.append(ToolStep(
            step_id=1,
            tool_name="sql_query",
            params={
                "intent": intent.model_dump(),
                "query_type": "detail",
                "table_hints": table_hints,
            },
        ))

        return QueryPlan(
            steps=[s.model_dump() for s in steps],
            needs_analysis=False,
            needs_export=False,
            target_tables=table_hints or [],
        )

    async def _plan_statistic_query(
        self,
        intent: IntentResult,
        user_context: Dict[str, Any],
        table_hints: Optional[List[str]] = None,
    ) -> QueryPlan:
        """Plan for statistical queries."""
        steps = []

        # Step 1: Generate SQL query with aggregation
        steps.append(ToolStep(
            step_id=1,
            tool_name="sql_query",
            params={
                "intent": intent.model_dump(),
                "query_type": "statistic",
                "table_hints": table_hints,
            },
        ))

        return QueryPlan(
            steps=[s.model_dump() for s in steps],
            needs_analysis=False,
            needs_export=False,
            target_tables=table_hints or [],
        )

    async def _plan_analysis_query(
        self,
        intent: IntentResult,
        user_context: Dict[str, Any],
        table_hints: Optional[List[str]] = None,
    ) -> QueryPlan:
        """Plan for analysis queries."""
        steps = []

        # Step 1: Fetch data
        steps.append(ToolStep(
            step_id=1,
            tool_name="sql_query",
            params={
                "intent": intent.model_dump(),
                "query_type": "analysis",
                "table_hints": table_hints,
            },
        ))

        # Step 2: Analyze data
        steps.append(ToolStep(
            step_id=2,
            tool_name="data_analysis",
            params={
                "analysis_type": self._determine_analysis_type(intent),
                "dimensions": intent.dimensions,
                "metrics": intent.metrics,
            },
            depends_on=[1],
        ))

        return QueryPlan(
            steps=[s.model_dump() for s in steps],
            needs_analysis=True,
            needs_export=False,
            target_tables=table_hints or [],
        )

    async def _plan_export_query(
        self,
        intent: IntentResult,
        user_context: Dict[str, Any],
        table_hints: Optional[List[str]] = None,
    ) -> QueryPlan:
        """Plan for export queries."""
        steps = []

        # Step 1: Fetch data
        steps.append(ToolStep(
            step_id=1,
            tool_name="sql_query",
            params={
                "intent": intent.model_dump(),
                "query_type": "export",
                "table_hints": table_hints,
            },
        ))

        # Step 2: Export to Excel
        steps.append(ToolStep(
            step_id=2,
            tool_name="export_excel",
            params={
                "format": "xlsx",
            },
            depends_on=[1],
        ))

        return QueryPlan(
            steps=[s.model_dump() for s in steps],
            needs_analysis=False,
            needs_export=True,
            target_tables=table_hints or [],
        )

    async def _plan_api_query(
        self,
        intent: IntentResult,
        user_context: Dict[str, Any],
        table_hints: Optional[List[str]] = None,
    ) -> QueryPlan:
        """Plan for API-based queries (inventory, sales, etc.)."""
        steps = []

        # Step 1: Call API to fetch data
        steps.append(ToolStep(
            step_id=1,
            tool_name="api_fetch",
            params={
                "intent": intent.model_dump(),
                "query_type": "api",
            },
        ))

        # Step 2: Analyze data if needed
        analysis_keywords = ["分析", "趋势", "对比", "比较"]
        user_query = str(intent.entities.get("original_query", ""))
        needs_analysis = any(kw in user_query for kw in analysis_keywords)

        if needs_analysis:
            steps.append(ToolStep(
                step_id=2,
                tool_name="data_analysis",
                params={
                    "analysis_type": self._determine_analysis_type(intent),
                    "dimensions": intent.dimensions,
                    "metrics": intent.metrics,
                },
                depends_on=[1],
            ))

        return QueryPlan(
            steps=[s.model_dump() for s in steps],
            needs_analysis=needs_analysis,
            needs_export=False,
            target_tables=[],
        )

    async def _plan_default(
        self,
        intent: IntentResult,
        user_context: Dict[str, Any],
        table_hints: Optional[List[str]] = None,
    ) -> QueryPlan:
        """Default planning strategy."""
        return await self._plan_statistic_query(intent, user_context, table_hints)

    def _determine_analysis_type(self, intent: IntentResult) -> str:
        """Determine the type of analysis based on intent."""
        if intent.time_range:
            return "trend"
        if intent.dimensions and len(intent.dimensions) > 1:
            return "comparison"
        return "summary"