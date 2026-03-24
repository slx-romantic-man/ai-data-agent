"""
ReAct Agent Engine - Implements Thought-Action-Observation reasoning loop.
"""
import re
import json
from typing import Optional, Dict, Any, List

from app.config.llm_config import BaseLLMClient, get_llm
from app.models.user import UserContext
from app.models.chat import (
    AgentResponse, ReasoningLog, ReasoningStep,
    DataResult, ChartConfig, IntentType
)
from app.models.permission import PermissionContext
from app.agent.prompts.react_prompt import (
    get_react_system_prompt,
    get_react_thought_prompt,
    get_react_continue_prompt,
    get_react_error_prompt,
    get_react_final_prompt
)
from app.agent.router.tool_router import ToolRouter, get_tool_router
from app.agent.router.api_router import get_api_router
from app.access.permission import get_rbac_manager


class ReActAgentEngine:
    """
    ReAct-style Agent Engine implementing Thought-Action-Observation loop.
    """

    MAX_ITERATIONS = 5  # Maximum reasoning iterations

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
    ):
        self._llm = llm_client
        self._tool_router: Optional[ToolRouter] = None
        self._initialized = False

    async def initialize(self):
        """Initialize async components."""
        if self._initialized:
            return
        self._tool_router = await get_tool_router()
        self._initialized = True

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

    async def process(
        self,
        user_query: str,
        user_context: UserContext,
        session_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        Process a user query using ReAct reasoning loop.
        Returns streaming-friendly AgentResponse with reasoning log.
        """
        reasoning_log = ReasoningLog()
        conversation_history = []
        all_data = []
        final_sql = ""

        try:
            # Build system prompt with tool descriptions
            tool_descriptions = self._build_tool_descriptions()
            api_config = self._build_api_config()

            system_prompt = get_react_system_prompt(
                tool_descriptions=tool_descriptions,
                user_role=user_context.role or "user",
                data_scope=user_context.department or "all",
                relevant_apis=api_config
            )

            # Initial thought prompt
            thought_prompt = get_react_thought_prompt(user_query)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": thought_prompt}
            ]

            iteration = 0
            is_finished = False

            while not is_finished and iteration < self.MAX_ITERATIONS:
                iteration += 1

                # Get LLM response (Thought and possibly Action)
                llm_response = await self.llm.chat(messages)

                # Parse the response for Thought and Action
                thought, action, answer = self._parse_llm_response(llm_response)

                # Create reasoning step
                step = ReasoningStep(
                    step_number=iteration,
                    thought=thought
                )

                if answer:
                    # Agent has reached final answer
                    is_finished = True
                    reasoning_log.final_answer = answer
                    reasoning_log.is_complete = True
                    step.observation = "Task completed."
                    reasoning_log.add_step(step)
                    break

                if action:
                    step.action = action

                    # Execute the tool
                    observation, result_data, sql = await self._execute_action(
                        action, user_query, user_context
                    )

                    step.observation = observation

                    if result_data:
                        all_data = result_data
                    if sql:
                        final_sql = sql

                    # Add to conversation for next iteration
                    messages.append({"role": "assistant", "content": llm_response})
                    messages.append({
                        "role": "user",
                        "content": get_react_continue_prompt(observation)
                    })
                else:
                    # No action parsed, might need to prompt again
                    messages.append({"role": "assistant", "content": llm_response})
                    messages.append({
                        "role": "user",
                        "content": "请继续你的思考，选择一个工具来执行。"
                    })

                reasoning_log.add_step(step)

            # Generate final text response
            final_text = await self._generate_final_response(
                user_query, reasoning_log, all_data
            )

            # Build data result
            data_result = None
            if all_data:
                data_result = DataResult(
                    columns=list(all_data[0].keys()) if all_data else [],
                    rows=all_data,
                    total=len(all_data),
                )

            # Generate chart config if applicable
            chart_config = None
            if all_data:
                chart_config = self._suggest_chart_config(all_data)

            return AgentResponse(
                text=final_text,
                data=data_result,
                chart_config=chart_config,
                sql=final_sql,
                intent=IntentType.API_QUERY,
                entities={},
                confidence=0.9,
                reasoning_log=reasoning_log
            )

        except Exception as e:
            # Add error to reasoning log
            if reasoning_log.steps:
                last_step = reasoning_log.get_last_step()
                if last_step:
                    last_step.observation = f"Error: {str(e)}"

            return AgentResponse(
                text=f"处理请求时发生错误：{str(e)}",
                intent=IntentType.UNKNOWN,
                reasoning_log=reasoning_log
            )

    def _parse_llm_response(
        self, response: str
    ) -> tuple[Optional[str], Optional[Dict], Optional[str]]:
        """
        Parse LLM response for Thought, Action, and Answer.
        Returns (thought, action_dict, answer)
        """
        thought = None
        action = None
        answer = None

        # Extract Thought
        thought_match = re.search(
            r'Thought:\s*(.+?)(?=\n(?:Action|Answer)|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if thought_match:
            thought = thought_match.group(1).strip()

        # Extract Action - 使用更健壮的JSON解析方法
        action_start = re.search(r'Action:\s*', response, re.IGNORECASE)
        if action_start:
            # 从 Action: 后面开始查找 JSON
            json_start_idx = action_start.end()
            # 找到第一个 { 的位置
            brace_start = response.find('{', json_start_idx)
            if brace_start != -1:
                # 使用括号匹配来找到完整的JSON
                brace_count = 0
                json_end = brace_start
                for i, char in enumerate(response[brace_start:], brace_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                action_str = response[brace_start:json_end].strip()

                try:
                    action = json.loads(action_str)
                except json.JSONDecodeError:
                    # Try to fix common JSON issues
                    try:
                        # Add missing quotes if needed
                        fixed = re.sub(r'(\{|,)\s*(\w+)\s*:', r'\1"\2":', action_str)
                        action = json.loads(fixed)
                    except:
                        pass

        # 确保 action 是字典类型
        if action is not None and not isinstance(action, dict):
            action = None

        # Extract Answer (final response)
        answer_match = re.search(
            r'Answer:\s*(.+?)$',
            response,
            re.DOTALL | re.IGNORECASE
        )
        if answer_match:
            answer = answer_match.group(1).strip()

        # If no explicit thought but we have response, use first part
        if not thought and response:
            lines = response.strip().split('\n')
            if lines:
                thought = lines[0] if 'Thought:' in lines[0] else lines[0][:200]

        return thought, action, answer

    async def _execute_action(
        self,
        action: Dict[str, Any],
        user_query: str,
        user_context: UserContext
    ) -> tuple[str, List[Dict], str]:
        """
        Execute an action and return (observation, data, sql).
        """
        tool_name = action.get("tool", action.get("name", ""))
        parameters = action.get("parameters", action.get("params", {}))

        observation = ""
        result_data = []
        sql = ""

        try:
            if tool_name == "api_fetch":
                # Use API router to determine endpoint
                api_router = get_api_router()
                api_id = parameters.get("api_id", "")
                endpoint = parameters.get("endpoint", "")

                if not api_id:
                    # Try to infer from query
                    route_result = api_router.route(user_query, {})
                    if route_result:
                        api_id, endpoint, api_params = route_result
                        parameters.update(api_params)

                tool = self.tool_router.get_tool("api_fetch")
                if tool:
                    result = await tool.execute(
                        {
                            "api_id": api_id,
                            "endpoint": endpoint,
                            "params": parameters
                        },
                        PermissionContext()  # Default permission
                    )

                    if result and result.data:
                        if isinstance(result.data, list):
                            result_data = result.data
                        elif isinstance(result.data, dict):
                            result_data = result.data.get("data", [])

                        # 构建包含统计信息的observation
                        observation = self._build_data_observation(result_data)
                        sql = f"API: {api_id}/{endpoint}"
                    else:
                        observation = "API调用成功，但未返回数据"

            elif tool_name == "sql_query":
                tool = self.tool_router.get_tool("sql_query")
                if tool:
                    result = await tool.execute(
                        {"sql": parameters.get("sql", "")},
                        PermissionContext()
                    )
                    if result and result.data:
                        result_data = result.data.get("data", [])
                        sql = result.data.get("sql", "")
                        observation = f"SQL执行成功，返回 {len(result_data)} 条数据"

            elif tool_name == "data_analysis":
                tool = self.tool_router.get_tool("data_analysis")
                if tool:
                    result = await tool.execute(
                        {
                            "data": parameters.get("data", []),
                            "user_query": user_query
                        },
                        PermissionContext()
                    )
                    if result and result.data:
                        observation = result.data.get("analysis", "分析完成")

            else:
                observation = f"未知工具: {tool_name}"

        except Exception as e:
            observation = f"工具执行失败: {str(e)}"

        return observation, result_data, sql

    async def _generate_final_response(
        self,
        user_query: str,
        reasoning_log: ReasoningLog,
        data: List[Dict]
    ) -> str:
        """Generate the final natural language response."""
        # Build reasoning history
        history_parts = []
        for step in reasoning_log.steps:
            if step.thought:
                history_parts.append(f"思考: {step.thought}")
            if step.action:
                history_parts.append(f"行动: {step.action}")
            if step.observation:
                history_parts.append(f"观察: {step.observation}")

        reasoning_history = "\n".join(history_parts)

        # If we already have a final answer, use it
        if reasoning_log.final_answer:
            return reasoning_log.final_answer

        # Generate response using LLM
        messages = [
            {
                "role": "system",
                "content": "你是企业数据分析助手，请用简洁专业的语言回答用户问题。"
            },
            {
                "role": "user",
                "content": get_react_final_prompt(reasoning_history, user_query)
            }
        ]

        return await self.llm.chat(messages)

    def _build_data_observation(self, data: List[Dict[str, Any]]) -> str:
        """
        构建包含统计信息的数据观察结果。
        自动识别日期字段和数值字段，提供关键统计信息。
        """
        if not data:
            return "API调用成功，但未返回数据"

        observation_parts = [f"获取到 {len(data)} 条数据"]

        # 识别日期字段（常见日期字段名）
        date_field_names = ['date', 'order_date', 'created_at', 'updated_at', 'time', 'datetime', 'start_date', 'end_date']

        # 收集所有字段的值
        field_values: Dict[str, List] = {}
        for row in data:
            for key, value in row.items():
                if key not in field_values:
                    field_values[key] = []
                if value is not None:
                    field_values[key].append(value)

        # 分析日期字段
        date_fields_found = []
        for field_name in date_field_names:
            if field_name in field_values and field_values[field_name]:
                values = field_values[field_name]
                # 检查是否为日期格式
                sample = str(values[0])
                if '-' in sample or '/' in sample:  # 简单判断是否为日期格式
                    unique_values = sorted(set(str(v) for v in values))
                    if len(unique_values) > 1:
                        date_range = f"{unique_values[0]} 至 {unique_values[-1]}"
                    else:
                        date_range = unique_values[0]
                    date_fields_found.append(f"{field_name}: {date_range}")

        if date_fields_found:
            observation_parts.append("日期范围: " + ", ".join(date_fields_found))

        # 分析数值字段（取前几个重要数值字段）
        numeric_stats = []
        for key, values in field_values.items():
            if key.lower() in ['id', '_id', 'order_id', 'item_id']:
                continue  # 跳过ID字段
            if values and isinstance(values[0], (int, float)):
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if numeric_values:
                    total = sum(numeric_values)
                    avg = total / len(numeric_values)
                    min_val = min(numeric_values)
                    max_val = max(numeric_values)
                    numeric_stats.append(
                        f"{key}: 总计{total:.2f}, 均值{avg:.2f}, 范围[{min_val:.2f}-{max_val:.2f}]"
                    )

        if numeric_stats:
            observation_parts.append("数值统计: " + "; ".join(numeric_stats[:3]))  # 最多显示3个数值字段

        # 显示数据样例（限制在3条以内）
        if len(data) > 0:
            sample_count = min(3, len(data))
            sample_str = json.dumps(data[:sample_count], ensure_ascii=False)
            observation_parts.append(f"数据样例: {sample_str}")

        return "。".join(observation_parts)

    def _build_tool_descriptions(self) -> str:
        """Build tool descriptions for system prompt."""
        return """
1. api_fetch - 调用API获取数据
   参数: {"api_id": "API标识", "endpoint": "端点", "params": {...}}

2. sql_query - 执行SQL查询
   参数: {"sql": "SELECT语句"}

3. data_analysis - 数据分析
   参数: {"data": 数据数组, "analysis_type": "分析类型"}

4. export_excel - 导出Excel
   参数: {"data": 数据数组, "filename": "文件名"}
"""

    def _build_api_config(self) -> str:
        """Build API configuration info."""
        try:
            api_router = get_api_router()
            apis = api_router.list_apis()
            if apis:
                api_list = []
                for api_id, info in apis.items():
                    api_list.append(f"- {api_id}: {info.get('name', api_id)}")
                return "可用API:\n" + "\n".join(api_list)
        except:
            pass
        return "暂无API配置"

    def _suggest_chart_config(
        self,
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
        if x_column and len(data) > 5:
            chart_type = "line"
        elif len(numeric_columns) > 2:
            chart_type = "pie"

        return ChartConfig(
            type=chart_type,
            x=x_column,
            y=y_column,
            title="数据统计",
        )


# Global ReAct agent engine instance
_react_agent_engine: Optional[ReActAgentEngine] = None


async def get_react_agent_engine() -> ReActAgentEngine:
    """Get or create ReAct agent engine instance."""
    global _react_agent_engine
    if _react_agent_engine is None:
        _react_agent_engine = ReActAgentEngine()
        await _react_agent_engine.initialize()
    return _react_agent_engine