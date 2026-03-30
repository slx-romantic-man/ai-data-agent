"""
Planner Node prompt templates.
"""

PLANNER_PROMPT = """你是一个数据查询规划师。根据用户查询和可用的数据源，生成一个结构化的执行计划。

用户查询：{user_query}

提取的过滤条件：
{extracted_filters}

可用的API列表：
{retrieved_apis}

可用的数据库表：
{retrieved_tables}

【重要约束】
- 如果"可用的API列表"显示"（无可用API）"，则必须使用sql_query工具查询数据库表
- 禁止虚构不存在的API（如order_statistics等），只能使用上面列出的真实API
- 禁止使用api_fetch工具调用不存在的API
- 【强制】api_id字段必须是字符串类型，使用"可用的API列表"中显示的API ID（如"alpha_vantage_stock"），禁止使用数字

请生成一个JSON格式的执行计划，包含以下字段：

1. steps: 执行步骤列表，每个步骤包含：
   - step_id: 步骤编号（从1开始）
   - tool: 工具类型（"api_fetch" 用于调用API，"sql_query" 用于查询数据库表，"python_exec" 用于执行Python代码进行数学计算）
   - api_id: API标识符（仅当tool为api_fetch时需要）
   - params: 调用参数（字典格式）
     * 对于 sql_query: 必须包含 "sql" 字段（完整的 SQL SELECT 语句）
     * 对于 api_fetch: 必须包含 "endpoint" 字段（从API的"可用端点"列表中选择）和 "params" 字段（包含API调用所需的参数）
     * 对于 python_exec: 必须包含 "code" 字段（Python代码字符串），可选 "context_keys" 字段（需要注入的前置步骤数据键列表）
   - description: 步骤描述
   - depends_on: 依赖的前置步骤ID列表（如果有）

2. reasoning: 规划推理过程

返回格式示例：
{{
    "steps": [
        {{
            "step_id": 1,
            "tool": "sql_query",
            "api_id": "",
            "params": {{
                "sql": "SELECT DATE(order_date) as date, COUNT(*) as order_count, SUM(amount) as total_amount FROM orders WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) GROUP BY DATE(order_date)"  # noqa: E501
            }},
            "description": "查询订单表获取最近7天的订单统计数据",
            "depends_on": []
        }},
        {{
            "step_id": 2,
            "tool": "python_exec",
            "api_id": "",
            "params": {{
                "code": "data = step_0_sql_query['data']; amounts = [row['total_amount'] for row in data]; result = sum(amounts) / len(amounts)",
                "context_keys": ["step_0_sql_query"]
            }},
            "description": "计算平均订单金额",
            "depends_on": [1]
        }}
    ],
    "reasoning": "用户想查询最近7天的订单统计并计算平均值，先用sql_query获取数据，再用python_exec计算"
}}

API调用示例：
{{
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
    "reasoning": "用户查询苹果股票数据，使用股票API的获取日线数据端点"
}}

规划原则：
1. 【强制】如果"可用的API列表"显示"（无可用API）"，必须使用sql_query工具，禁止使用api_fetch
2. 【强制】禁止虚构或假设不存在的API，只能使用"可用的API列表"中明确列出的API
3. 如果有相关API且API列表非空，优先使用api_fetch工具调用API
4. 使用sql_query时，params必须包含完整可执行的SQL SELECT语句（"sql"字段）
5. SQL语句中的表名必须来自"可用的数据库表"列表，不可使用不存在的表
6. SQL的WHERE条件只能使用"可用的数据库表"结构中列出的字段，禁止使用不存在的列
7. 时间过滤条件必须基于表结构中真实存在的日期/时间字段
8. 【python_exec使用场景】当需要进行数学计算（增长率、平均值、百分比等）时使用python_exec工具
9. 【python_exec数据引用】前置步骤的数据通过变量名 "step_{{idx}}_{{tool}}" 注入，idx是执行顺序索引（从0开始，不是step_id）。例如：step_id=1的sql_query结果为 step_0_sql_query，step_id=2的api_fetch结果为 step_1_api_fetch，step_id=3的python_exec结果为 step_2_python_exec
10. 【python_exec代码规范】代码必须将计算结果赋值给变量"result"，引用前置数据时使用完整变量名如 step_0_sql_query['data']。注意：step_id=1对应step_0，step_id=2对应step_1，以此类推。【严格禁止】使用import语句（包括import json、import pandas等），只能使用Python内置函数（sum, len, round, min, max, sorted, float, int, str, list, dict等）
11. 保持步骤简洁，避免冗余查询

请只返回JSON，不要包含其他内容。"""


def get_planner_prompt(
    user_query: str, extracted_filters: dict, retrieved_apis: list
) -> str:
    """Get planner prompt."""
    import json

    filters_str = json.dumps(extracted_filters, ensure_ascii=False, indent=2)

    # 分离 APIs 和 Tables
    apis = []
    tables = []
    for item in retrieved_apis:
        item_type = item.get('type', '')
        if item_type in ('table', 'sql_table'):
            tables.append(item)
        else:
            apis.append(item)

    # 格式化API列表
    apis_str = ""
    if apis:
        for idx, api in enumerate(apis, 1):
            # 使用 config_id (字符串) 作为 API 标识符
            config_id = api.get('config_id')
            if not config_id:
                # 如果没有 config_id，使用 api_id 转为字符串
                config_id = str(api.get('api_id') or api.get('id', 'unknown'))
            name = api.get('name', 'N/A')
            desc = api.get('description', 'N/A')

            apis_str += f"{idx}. API ID: {config_id}\n"
            apis_str += f"   名称: {name}\n"
            apis_str += f"   描述: {desc}\n"

            # 添加 endpoints 信息
            endpoints = api.get('endpoints', {})
            if endpoints:
                apis_str += f"   可用端点:\n"
                for endpoint_name, endpoint_config in endpoints.items():
                    if isinstance(endpoint_config, dict):
                        endpoint_desc = endpoint_config.get('description', 'N/A')
                        endpoint_path = endpoint_config.get('path', 'N/A')
                        apis_str += f"     - {endpoint_name}: {endpoint_desc} (路径: {endpoint_path})\n"

                        # 添加参数信息
                        endpoint_params = endpoint_config.get('params', {})
                        default_params = endpoint_config.get('default_params', {})
                        required_params = endpoint_config.get('required_params', [])

                        if endpoint_params:
                            apis_str += f"       参数: {json.dumps(endpoint_params, ensure_ascii=False)}\n"
                        if default_params:
                            apis_str += f"       默认参数: {json.dumps(default_params, ensure_ascii=False)}\n"
                        if required_params:
                            apis_str += f"       必需参数: {required_params}\n"

            # 如果没有 endpoints，尝试显示 params
            if not endpoints:
                params = api.get('params', {})
                if params:
                    apis_str += f"   参数: {json.dumps(params, ensure_ascii=False)}\n"

            apis_str += "\n"
    else:
        apis_str = "（无可用API）\n"

    # 格式化数据库表列表
    tables_str = ""
    if tables:
        for idx, table in enumerate(tables, 1):
            table_name = table.get('name', 'unknown')
            tables_str += f"{idx}. 表名: {table_name}\n"
            tables_str += f"   描述: {table.get('description', 'N/A')}\n"
            if 'schema' in table:
                tables_str += f"   结构: {table.get('schema', '')}\n"
            tables_str += "\n"
    else:
        tables_str = "（无可用数据库表）\n"

    return PLANNER_PROMPT.format(
        user_query=user_query,
        extracted_filters=filters_str,
        retrieved_apis=apis_str,
        retrieved_tables=tables_str
    )
