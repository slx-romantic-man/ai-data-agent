"""
Agent Engine - Main orchestrator for AI Data Agent.
Coordinates intent recognition, query planning, permission inference, and tool execution.
"""
from typing import Optional, Dict, Any, List
import uuid
import json

from app.config.llm_config import BaseLLMClient, get_llm
from app.models.user import UserContext
from app.models.chat import AgentResponse, IntentResult, QueryPlan, DataResult, ChartConfig
from app.models.permission import PermissionContext
from app.agent.core.intent_recognizer import IntentRecognizer
from app.agent.core.query_planner import QueryPlanner
from app.agent.core.permission_inferencer import PermissionInferencer
from app.agent.core.sql_generator import SQLGenerator
from app.agent.core.data_analyzer import DataAnalyzer
from app.agent.router.tool_router import ToolRouter, get_tool_router
from app.agent.router.api_router import get_api_router
from app.agent.prompts.system_prompt import get_system_prompt
from app.access.permission import get_rbac_manager


class AgentEngine:
    """
    Main Agent Engine that orchestrates the entire query processing pipeline.
    """

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        table_schema: str = "",
    ):
        self._llm = llm_client
        self._table_schema = table_schema
        self._initialized = False

        # Components (lazy initialization)
        self._intent_recognizer: Optional[IntentRecognizer] = None
        self._query_planner: Optional[QueryPlanner] = None
        self._permission_inferencer: Optional[PermissionInferencer] = None
        self._sql_generator: Optional[SQLGenerator] = None
        self._data_analyzer: Optional[DataAnalyzer] = None
        self._tool_router: Optional[ToolRouter] = None

    async def initialize(self):
        """Initialize all async components."""
        if self._initialized:
            return

        self._intent_recognizer = IntentRecognizer(self._llm)
        self._query_planner = QueryPlanner()
        self._permission_inferencer = PermissionInferencer(get_rbac_manager())
        self._sql_generator = SQLGenerator(self._llm)
        self._data_analyzer = DataAnalyzer(self._llm)
        self._tool_router = await get_tool_router()

        self._initialized = True

    @property
    def intent_recognizer(self) -> IntentRecognizer:
        if self._intent_recognizer is None:
            self._intent_recognizer = IntentRecognizer(self._llm)
        return self._intent_recognizer

    @property
    def query_planner(self) -> QueryPlanner:
        if self._query_planner is None:
            self._query_planner = QueryPlanner()
        return self._query_planner

    @property
    def permission_inferencer(self) -> PermissionInferencer:
        if self._permission_inferencer is None:
            self._permission_inferencer = PermissionInferencer(get_rbac_manager())
        return self._permission_inferencer

    @property
    def sql_generator(self) -> SQLGenerator:
        if self._sql_generator is None:
            self._sql_generator = SQLGenerator(self._llm)
        return self._sql_generator

    @property
    def data_analyzer(self) -> DataAnalyzer:
        if self._data_analyzer is None:
            self._data_analyzer = DataAnalyzer(self._llm)
        return self._data_analyzer

    @property
    def tool_router(self) -> ToolRouter:
        if self._tool_router is None:
            raise RuntimeError("ToolRouter not initialized. Call initialize() first.")
        return self._tool_router

    @property
    def llm(self) -> BaseLLMClient:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def set_table_schema(self, schema: str):
        """Set the database schema for SQL generation."""
        self._table_schema = schema

    async def process(
        self,
        user_query: str,
        user_context: UserContext,
        session_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Process a user query and return a response.

        Args:
            user_query: User's natural language query
            user_context: User context with permissions
            session_id: Optional session ID for conversation continuity

        Returns:
            AgentResponse with text, data, and optional chart config
        """
        try:
            # 1. Intent Recognition
            intent = await self.intent_recognizer.recognize(user_query)

            # 2. Permission Inference
            permission = await self.permission_inferencer.infer(user_context)

            # 3. Query Planning
            plan = await self.query_planner.plan(intent, user_context.model_dump())

            # 4. Execute Plan
            results = await self._execute_plan(plan, user_query, intent, permission)

            # 5. Generate Response
            response = await self._generate_response(
                user_query=user_query,
                intent=intent,
                results=results,
                permission=permission,
            )

            return response

        except PermissionError as e:
            return AgentResponse(
                text=f"抱歉，您没有权限执行此操作：{str(e)}",
                intent=IntentResult(intent_type="unknown").intent_type,
            )
        except Exception as e:
            return AgentResponse(
                text=f"处理您的请求时发生错误：{str(e)}",
                intent=IntentResult(intent_type="unknown").intent_type,
            )

    async def _execute_plan(
        self,
        plan: QueryPlan,
        user_query: str,
        intent: IntentResult,
        permission: PermissionContext,
    ) -> Dict[str, Any]:
        """Execute the query plan steps."""
        results = {}

        for step in plan.steps:
            step_id = step.get("step_id")
            tool_name = step.get("tool_name")
            params = step.get("params", {})

            # Get tool from router
            tool = self.tool_router.get_tool(tool_name)
            if not tool:
                continue

            # Prepare parameters based on tool type
            if tool_name == "sql_query":
                # Generate SQL
                sql = await self.sql_generator.generate(
                    user_query=user_query,
                    intent=intent,
                    permission=permission,
                    table_schema=self._table_schema,
                )
                params["sql"] = sql

            elif tool_name == "api_fetch":
                # Use API router to determine API and endpoint
                from app.agent.router.api_router import get_api_router
                api_router = get_api_router()
                route_result = api_router.route(
                    user_query,
                    intent.entities
                )
                if route_result:
                    api_id, endpoint, api_params = route_result
                    params["api_id"] = api_id
                    params["endpoint"] = endpoint
                    params["params"] = api_params

            elif tool_name == "data_analysis":
                # Get data from previous step
                sql_result = results.get("sql_query")
                api_result = results.get("api_fetch")
                if sql_result:
                    if hasattr(sql_result, 'data') and sql_result.data:
                        params["data"] = sql_result.data.get("data", [])
                    elif isinstance(sql_result, dict):
                        params["data"] = sql_result.get("data", [])
                elif api_result:
                    if hasattr(api_result, 'data') and api_result.data:
                        params["data"] = api_result.data
                    elif isinstance(api_result, dict):
                        params["data"] = api_result.get("data", [])
                params["user_query"] = user_query

            elif tool_name == "export_excel":
                # Get data from previous step
                sql_result = results.get("sql_query")
                api_result = results.get("api_fetch")
                if sql_result:
                    if hasattr(sql_result, 'data') and sql_result.data:
                        params["data"] = sql_result.data.get("data", [])
                    elif isinstance(sql_result, dict):
                        params["data"] = sql_result.get("data", [])
                elif api_result:
                    if hasattr(api_result, 'data') and api_result.data:
                        params["data"] = api_result.data
                    elif isinstance(api_result, dict):
                        params["data"] = api_result.get("data", [])

            # Execute tool
            result = await tool.execute(params, permission)
            results[tool_name] = result

        return results

    async def _generate_response(
        self,
        user_query: str,
        intent: IntentResult,
        results: Dict[str, Any],
        permission: PermissionContext,
    ) -> AgentResponse:
        """Generate the final response from results."""
        from app.models.tool import ToolResult

        # Get data from SQL or API result
        sql_result = results.get("sql_query")
        api_result = results.get("api_fetch")
        data = []
        sql = ""

        if sql_result:
            if isinstance(sql_result, ToolResult):
                if sql_result.data:
                    data = sql_result.data.get("data", [])
                    sql = sql_result.data.get("sql", "")
            elif isinstance(sql_result, dict):
                data = sql_result.get("data", [])
                sql = sql_result.get("sql", "")
        elif api_result:
            if isinstance(api_result, ToolResult):
                if api_result.data:
                    data = api_result.data if isinstance(
                        api_result.data, list
                    ) else []
            elif isinstance(api_result, dict):
                data = api_result.get("data", [])

        # Get analysis if available
        analysis_result = results.get("data_analysis")
        analysis = {}
        if analysis_result:
            if isinstance(analysis_result, ToolResult):
                analysis = analysis_result.data or {}
            elif isinstance(analysis_result, dict):
                analysis = analysis_result

        # Generate text response using LLM
        text = await self._generate_text_response(user_query, intent, data, analysis)

        # Build data result
        data_result = None
        if data:
            data_result = DataResult(
                columns=list(data[0].keys()) if data else [],
                rows=data,
                total=len(data),
            )

        # Generate chart config if applicable
        chart_config = None
        if intent.intent_type.value in ["data_statistic", "data_analysis"] and data:
            chart_config = self._suggest_chart_config(intent, data)

        return AgentResponse(
            text=text,
            data=data_result,
            chart_config=chart_config,
            sql=sql,
            intent=intent.intent_type,
            entities=intent.entities,
            confidence=intent.confidence,
        )

    async def _generate_text_response(
        self,
        user_query: str,
        intent: IntentResult,
        data: List[Dict[str, Any]],
        analysis: Dict[str, Any],
    ) -> str:
        """Generate natural language response."""
        # Build context for LLM
        context = f"""
用户问题：{user_query}
意图类型：{intent.intent_type.value}
数据行数：{len(data)}
"""

        if analysis:
            context += f"\n分析结果：\n{analysis.get('analysis', '')}"

        if data:
            # Add sample data
            context += f"\n数据样本（前5行）：\n{json.dumps(data[:5], ensure_ascii=False, indent=2)}"

        # Generate response
        messages = [
            {"role": "system", "content": "你是企业的数据分析助手，请用简洁专业的语言回答用户问题。"},
            {"role": "user", "content": context + "\n\n请根据以上信息，用自然语言回答用户的问题。"}
        ]

        response = await self.llm.chat(messages)
        return response

    def _suggest_chart_config(
        self,
        intent: IntentResult,
        data: List[Dict[str, Any]],
    ) -> Optional[ChartConfig]:
        """Suggest chart configuration based on data."""
        if not data:
            return None

        columns = list(data[0].keys())

        # Find time column
        time_columns = ["date", "time", "datetime", "created_at", "day", "month"]
        x_column = None
        for col in columns:
            if col.lower() in time_columns:
                x_column = col
                break

        # Find value column
        numeric_columns = []
        for key, value in data[0].items():
            if isinstance(value, (int, float)):
                numeric_columns.append(key)

        if not numeric_columns:
            return None

        y_column = numeric_columns[0]

        # Determine chart type
        chart_type = "bar"
        if x_column and intent.time_range:
            chart_type = "line"
        elif len(numeric_columns) > 2:
            chart_type = "pie"

        return ChartConfig(
            type=chart_type,
            x=x_column,
            y=y_column,
            title=intent.metrics[0] if intent.metrics else "数据统计",
        )


# Global agent engine instance
_agent_engine: Optional[AgentEngine] = None


async def get_agent_engine() -> AgentEngine:
    """Get or create agent engine instance."""
    global _agent_engine
    if _agent_engine is None:
        _agent_engine = AgentEngine()
        await _agent_engine.initialize()
    return _agent_engine