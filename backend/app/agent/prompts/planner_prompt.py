"""
Planner Node prompt templates.
"""

PLANNER_PROMPT = """你是一个数据查询规划师。根据用户查询和可用的API列表，生成一个结构化的执行计划。

用户查询：{user_query}

提取的过滤条件：
{extracted_filters}

可用的API列表（Top-10 相关API）：
{retrieved_apis}

请生成一个JSON格式的执行计划，包含以下字段：

1. steps: 执行步骤列表，每个步骤包含：
   - step_id: 步骤编号（从1开始）
   - tool: 工具类型（"api_fetch" 或 "sql_query"）
   - api_id: API标识符（如果是api_fetch）
   - params: 调用参数（字典格式）
   - description: 步骤描述
   - depends_on: 依赖的前置步骤ID列表（如果有）

2. reasoning: 规划推理过程

返回格式示例：
{{
    "steps": [
        {{
            "step_id": 1,
            "tool": "api_fetch",
            "api_id": "sales_daily",
            "params": {{
                "start_date": "2024-01-01",
                "end_date": "2024-01-07",
                "region": "华东"
            }},
            "description": "获取华东地区最近7天的销售数据",
            "depends_on": []
        }},
        {{
            "step_id": 2,
            "tool": "api_fetch",
            "api_id": "sales_trend",
            "params": {{
                "metric": "sales_amount",
                "dimension": "date"
            }},
            "description": "分析销售趋势",
            "depends_on": [1]
        }}
    ],
    "reasoning": "用户想查询华东地区的销售数据并分析趋势，因此先调用sales_daily获取原始数据，再调用sales_trend进行趋势分析"
}}

规划原则：
1. 优先使用retrieved_apis中的API
2. 如果需要多个数据源，按依赖关系排序
3. 参数必须从extracted_filters中提取或合理推断
4. 保持步骤简洁，避免冗余查询

请只返回JSON，不要包含其他内容。"""


def get_planner_prompt(user_query: str, extracted_filters: dict, retrieved_apis: list) -> str:
    """Get planner prompt."""
    import json

    filters_str = json.dumps(extracted_filters, ensure_ascii=False, indent=2)

    # 格式化API列表
    apis_str = ""
    for idx, api in enumerate(retrieved_apis, 1):
        apis_str += f"{idx}. API ID: {api.get('api_id', 'unknown')}\n"
        apis_str += f"   描述: {api.get('description', 'N/A')}\n"
        apis_str += f"   参数: {json.dumps(api.get('params', {}), ensure_ascii=False)}\n\n"

    return PLANNER_PROMPT.format(
        user_query=user_query,
        extracted_filters=filters_str,
        retrieved_apis=apis_str
    )
