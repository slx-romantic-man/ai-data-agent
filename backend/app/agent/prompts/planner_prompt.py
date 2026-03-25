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

请生成一个JSON格式的执行计划，包含以下字段：

1. steps: 执行步骤列表，每个步骤包含：
   - step_id: 步骤编号（从1开始）
   - tool: 工具类型（"api_fetch" 用于调用API，"sql_query" 用于查询数据库表）
   - api_id: API标识符（仅当tool为api_fetch时需要）
   - params: 调用参数（字典格式）
     * 对于 sql_query: 必须包含 "sql" 字段（完整的 SQL SELECT 语句）
     * 对于 api_fetch: 包含 API 所需的参数
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
        }}
    ],
    "reasoning": "用户想查询最近7天的订单统计，使用sql_query工具查询orders表"
}}

规划原则：
1. 【强制】如果"可用的API列表"显示"（无可用API）"，必须使用sql_query工具，禁止使用api_fetch
2. 【强制】禁止虚构或假设不存在的API，只能使用"可用的API列表"中明确列出的API
3. 如果有相关API且API列表非空，优先使用api_fetch工具调用API
4. 使用sql_query时，params必须包含完整可执行的SQL SELECT语句（"sql"字段）
5. SQL语句中的表名必须来自"可用的数据库表"列表，不可使用不存在的表
6. SQL的WHERE条件只能使用"可用的数据库表"结构中列出的字段，禁止使用不存在的列
7. 时间过滤条件必须基于表结构中真实存在的日期/时间字段
8. 保持步骤简洁，避免冗余查询

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
            api_id = api.get('api_id', 'unknown')
            desc = api.get('description', 'N/A')
            params = json.dumps(api.get('params', {}), ensure_ascii=False)
            apis_str += f"{idx}. API ID: {api_id}\n"
            apis_str += f"   描述: {desc}\n"
            apis_str += f"   参数: {params}\n\n"
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
