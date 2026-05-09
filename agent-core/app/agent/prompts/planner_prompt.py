"""
Planner Node prompt templates.
"""

PLANNER_PROMPT = """你是一个数据查询规划师。根据用户查询和可用的数据源，生成一个结构化的执行计划。

用户查询：{user_query}
提取的过滤条件：{extracted_filters}
可用的API列表：{retrieved_apis}
可用的数据库表：{retrieved_tables}

【重要约束】
- 无可用API时必须使用sql_query，禁止使用api_fetch
- 禁止虚构不存在的API，api_id必须是列表中真实的ID（字符串，不能是数字）
- SQL表名必须来自可用列表，WHERE条件只能用表结构中的字段
- python_exec仅用于数学计算（增长率、平均值、百分比等），代码必须赋值给变量"result"，禁止import语句
- python_exec数据引用：前置步骤数据通过 "step_{{idx}}_{{tool}}" 注入，idx从0开始（step_id=1对应step_0，step_id=2对应step_1）

【步骤字段】每个步骤包含：
step_id(从1开始)|tool("api_fetch"|"sql_query"|"python_exec")|api_id(仅api_fetch)|params(sql|endpoint+params|code)|description|depends_on

返回格式示例：
{{"steps": [{{"step_id": 1, "tool": "sql_query", "api_id": "", "params": {{"sql": "SELECT DATE(order_date) as date, COUNT(*) as order_count FROM orders WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) GROUP BY DATE(order_date)"}}, "description": "查询最近7天订单", "depends_on": []}}, {{"step_id": 2, "tool": "python_exec", "api_id": "", "params": {{"code": "data = step_0_sql_query['data']; result = sum([row['order_count'] for row in data]) / len(data)", "context_keys": ["step_0_sql_query"]}}, "description": "计算平均订单数", "depends_on": [1]}}], "reasoning": "先用SQL获取数据，再用Python计算平均值"}}

API调用示例：
{{"steps": [{{"step_id": 1, "tool": "api_fetch", "api_id": "alpha_vantage_stock", "params": {{"endpoint": "获取日线数据", "params": {{"symbol": "AAPL", "outputsize": "compact"}}}}, "description": "获取苹果股票数据", "depends_on": []}}], "reasoning": "用户查询股票数据，使用股票API获取日线数据"}}

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
