"""
Combined intent recognition + planning prompt templates.
Single LLM call for both intent understanding and execution planning.
"""

INTENT_PLANNER_PROMPT = """你是一个智能数据查询规划师。根据用户查询和可用的数据源，完成两项任务：
1. 识别用户意图并提取关键信息
2. 生成结构化的执行计划

用户查询：{user_query}

可用的API列表：
{retrieved_apis}

可用的数据库表：
{retrieved_tables}

系统已配置的API列表（用于意图参考）：
{api_list}

请返回以下JSON格式的结果：

## 意图识别部分
1. intent_type: 意图类型
   - "api_query": 调用API查询数据（默认类型）
   - "data_detail": 查询数据明细
   - "data_statistic": 统计汇总
   - "data_analysis": 数据分析
   - "data_export": 导出数据

2. entities: 提取的实体信息
   - time_range: 时间范围
   - trading_day_count: 交易日数量
   - stock_symbol: 股票代码
   - market: 股票市场（US/CN/HK）
   - location: 地点
   - business: 业务类型
   - department: 部门
   - api_hint: 建议使用的API ID

3. metrics: 指标名称列表
4. dimensions: 维度列表
5. confidence: 置信度（0-1）
6. missing_info: 缺失的关键信息列表（仅当用户输入本身缺少必需参数时才填写）
   - 注意：相对时间（最近N天、本周、本月等）不算缺失信息
   - 注意：系统没有配置相关API不属于"缺失信息"
   - 如果信息完整，必须返回null
7. clarification_question: 如果有缺失信息，生成友好的反问（如果信息完整则为null）

## 执行计划部分
8. steps: 执行步骤列表，每个步骤包含：
   - step_id: 步骤编号（从1开始）
   - tool: 工具类型（"api_fetch", "sql_query", "python_exec"）
   - api_id: API标识符（仅当tool为api_fetch时需要）
   - params: 调用参数（字典格式）
     * 对于 sql_query: 必须包含 "sql" 字段（完整的 SQL SELECT 语句）
     * 对于 api_fetch: 必须包含 "endpoint" 和 "params" 字段
     * 对于 python_exec: 必须包含 "code" 字段
   - description: 步骤描述
   - depends_on: 依赖的前置步骤ID列表
9. reasoning: 规划推理过程

【重要约束】
- 如果"可用的API列表"显示"（无可用API）"，则必须使用sql_query工具
- 禁止虚构不存在的API，只能使用上面列出的真实API
- api_id字段必须是字符串类型
- SQL语句中的表名必须来自"可用的数据库表"列表
- SQL的WHERE条件只能使用表结构中真实存在的字段
- python_exec代码禁止使用import语句，只能使用Python内置函数

返回格式示例（信息完整）：
{{
    "intent_type": "api_query",
    "entities": {{
        "stock_symbol": "AAPL",
        "market": "US",
        "time_range": {{"description": "最近7天"}},
        "api_hint": "stock_price"
    }},
    "metrics": ["股价", "涨跌幅"],
    "dimensions": ["日期"],
    "confidence": 0.95,
    "missing_info": null,
    "clarification_question": null,
    "steps": [
        {{
            "step_id": 1,
            "tool": "api_fetch",
            "api_id": "alpha_vantage_stock",
            "params": {{
                "endpoint": "获取日线数据",
                "params": {{
                    "symbol": "AAPL",
                    "outputsize": "compact"
                }}
            }},
            "description": "获取苹果股票最近的交易数据",
            "depends_on": []
        }}
    ],
    "reasoning": "用户查询苹果股票数据，使用股票API获取日线数据"
}}

返回格式示例（信息不完整）：
{{
    "intent_type": "api_query",
    "entities": {{
        "api_hint": "weather_api"
    }},
    "metrics": ["天气"],
    "dimensions": [],
    "confidence": 0.8,
    "missing_info": ["地点"],
    "clarification_question": "请问您想查询哪个城市的天气？例如：北京、上海、广州。",
    "steps": [],
    "reasoning": "用户查询意图为天气查询，但缺少地点信息，无法生成执行计划"
}}

请只返回JSON，不要包含其他内容。"""


def get_intent_planner_prompt(
    user_query: str,
    retrieved_apis: list,
    retrieved_tables: list = None,
    api_list: str = "",
    history: list = None
) -> str:
    """Get combined intent + planner prompt."""
    import json

    # 分离 APIs 和 Tables
    apis = []
    tables = []
    for item in (retrieved_apis or []):
        item_type = item.get('type', '')
        if item_type in ('table', 'sql_table'):
            tables.append(item)
        else:
            apis.append(item)

    # 格式化API列表
    apis_str = ""
    if apis:
        for idx, api in enumerate(apis, 1):
            config_id = api.get('config_id')
            if not config_id:
                config_id = str(api.get('api_id') or api.get('id', 'unknown'))
            name = api.get('name', 'N/A')
            desc = api.get('description', 'N/A')

            apis_str += f"{idx}. API ID: {config_id}\n"
            apis_str += f"   名称: {name}\n"
            apis_str += f"   描述: {desc}\n"

            endpoints = api.get('endpoints', {})
            if endpoints:
                apis_str += f"   可用端点:\n"
                for endpoint_name, endpoint_config in endpoints.items():
                    if isinstance(endpoint_config, dict):
                        endpoint_desc = endpoint_config.get('description', 'N/A')
                        endpoint_path = endpoint_config.get('path', 'N/A')
                        apis_str += f"     - {endpoint_name}: {endpoint_desc} (路径: {endpoint_path})\n"

                        endpoint_params = endpoint_config.get('params', {})
                        default_params = endpoint_config.get('default_params', {})
                        required_params = endpoint_config.get('required_params', [])

                        if endpoint_params:
                            apis_str += f"       参数: {json.dumps(endpoint_params, ensure_ascii=False)}\n"
                        if default_params:
                            apis_str += f"       默认参数: {json.dumps(default_params, ensure_ascii=False)}\n"
                        if required_params:
                            apis_str += f"       必需参数: {required_params}\n"

            if not endpoints:
                params = api.get('params', {})
                if params:
                    apis_str += f"   参数: {json.dumps(params, ensure_ascii=False)}\n"

            apis_str += "\n"
    else:
        apis_str = "（无可用API）\n"

    # 格式化数据库表列表
    tables_str = ""
    if retrieved_tables:
        for idx, table in enumerate(retrieved_tables, 1):
            table_name = table.get('name', 'unknown')
            tables_str += f"{idx}. 表名: {table_name}\n"
            tables_str += f"   描述: {table.get('description', 'N/A')}\n"
            if 'schema' in table:
                tables_str += f"   结构: {table.get('schema', '')}\n"
            tables_str += "\n"
    else:
        tables_str = "（无可用数据库表）\n"

    # Build history section
    history_section = ""
    if history and len(history) > 0:
        recent_history = history[-6:]
        history_lines = []
        for msg in recent_history:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            history_lines.append(f"{role}: {content}")
        history_section = f"""

### 对话历史
以下是最近的对话记录，请结合历史上下文理解用户完整意图：
{chr(10).join(history_lines)}
"""

    return INTENT_PLANNER_PROMPT.format(
        user_query=user_query,
        retrieved_apis=apis_str,
        retrieved_tables=tables_str,
        api_list=api_list
    ) + history_section
