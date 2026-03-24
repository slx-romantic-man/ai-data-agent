"""
ReAct-style prompt templates for AI Agent reasoning.
Implements Thought -> Action -> Observation loop.
"""

# JSON example for tool usage
_ACTION_JSON_EXAMPLE = (
    '{"tool": "api_fetch", "parameters": {"api_id": '
    '"API配置ID(必须来自用户可用API列表)", "endpoint": "端点名称", '
    '"params": {}}}'
)

REACT_SYSTEM_PROMPT = """你是一个企业数据分析AI Agent，采用ReAct推理框架工作。

## 工作方式
你将通过"思考-行动-观察"循环来解决问题：
- Thought: 分析当前情况，思考下一步该做什么
- Action: 选择并执行一个工具
- Observation: 观察工具返回的结果
- 重复以上步骤直到任务完成
- Answer: 给出最终答案

## 可用工具
{tool_descriptions}

## 用户可用的API
{relevant_apis}

## 工具使用格式
当你需要使用工具时，按以下格式输出：

Thought: [你的思考过程]
Action: __ACTION_JSON_EXAMPLE__

## 数据权限规则
- 只能查询用户权限范围内的数据
- 用户角色: {user_role}
- 数据范围: {data_scope}
- 敏感字段自动脱敏

## 缺失信息处理规则
**重要**: 当用户查询缺少关键信息时，你应该：
1. 识别缺失的具体信息（如IP地址、订单号、时间范围等）
2. 生成清晰的反问，说明需要什么信息以及为什么需要
3. 等待用户补充后再执行查询

**示例**：
- 用户："查询IP的归属地" → 你应该回答："请提供需要查询的IP地址"
- 用户："查看订单详情" → 你应该回答："请提供订单号，或者指定要查询的时间范围"
- 用户："导出库存数据" → 你应该回答："请指定需要导出的商品类别或时间范围"

**不要在缺少必需参数的情况下强行调用API**，这会导致查询失败。

## 执行规则与格式
1. **当前日期**: {current_date}。
2. **参数规范**: 严禁在 API 参数中输入 "last_7_days" 等模糊词，需使用具体日期。
3. **每次输出一个步骤**：每次只输出一个 Thought 和一个 Action，或者回答。
4. **停止标记**：当你认为有足够信息回答问题时，必须输出：
   Thought: [最终思考]
   Answer: [最终回答]

## 记忆与上下文规范
1. **优先参考历史**：针对追问，优先使用之前的 Observation 数据。
2. **保持约束一致性**：自动沿用之前对话已限定的时间范围等约束。
3. **逻辑连贯性**：结论不得与之前已确认的事实产生矛盾。

请开始你的推理过程。"""

REACT_THOUGHT_PROMPT = """用户问题: {user_query}

{conversation_history}

请开始你的思考过程。记住：
1. 首先分析问题，确定需要什么信息
2. 规划如何获取 these 信息
3. 选择合适的工具执行
4. 基于结果继续推理直到得出答案

以 "Thought:" 开头开始你的回答。"""

REACT_CONTINUE_PROMPT = """Observation: {observation}

请基于以上观察结果继续你的推理。如果你已经有足够信息回答用户问题，请给出最终Answer。否则继续Thought-Action循环。

继续你的思考过程："""

REACT_FINAL_PROMPT = """基于以下推理过程，请给出简洁专业的最终回答：

推理历史：
{reasoning_history}

用户原始问题：{user_query}

请用自然语言回答（不要包含Thought/Action/Observation标签）："""

REACT_ERROR_PROMPT = """工具执行出错：
{error_message}

请思考如何处理这个错误，可以：
1. 重试（如果可能是临时错误）
2. 尝试其他方法
3. 向用户说明情况

继续你的思考过程："""


def get_react_system_prompt(
    tool_descriptions: str = "",
    user_role: str = "user",
    data_scope: str = "all",
    relevant_apis: str = "",
    current_date: str = ""
) -> str:
    """
    Get ReAct system prompt with configured parameters.

    Args:
        tool_descriptions: Available tool descriptions
        user_role: User's role (admin, manager, employee, etc.)
        data_scope: User's data scope (department, all, etc.)
        relevant_apis: Formatted string of relevant APIs for the query
        current_date: Current date for temporal queries

    Returns:
        Formatted system prompt string
    """
    prompt = REACT_SYSTEM_PROMPT.format(
        tool_descriptions=tool_descriptions,
        user_role=user_role,
        data_scope=data_scope,
        relevant_apis=relevant_apis,
        current_date=current_date
    )
    # Replace the placeholder with the actual JSON example
    return prompt.replace("__ACTION_JSON_EXAMPLE__", _ACTION_JSON_EXAMPLE)


def get_react_thought_prompt(
    user_query: str,
    conversation_history: str = ""
) -> str:
    """Get initial thought prompt for a new query."""
    return REACT_THOUGHT_PROMPT.format(
        user_query=user_query,
        conversation_history=conversation_history
    )


def get_react_continue_prompt(observation: str) -> str:
    """Get continuation prompt after receiving an observation."""
    return REACT_CONTINUE_PROMPT.format(observation=observation)


def get_react_error_prompt(error_message: str) -> str:
    """Get error handling prompt."""
    return REACT_ERROR_PROMPT.format(error_message=error_message)


def get_react_final_prompt(
    reasoning_history: str,
    user_query: str
) -> str:
    """Get final answer generation prompt."""
    return REACT_FINAL_PROMPT.format(
        reasoning_history=reasoning_history,
        user_query=user_query
    )