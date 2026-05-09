"""
Intent recognition prompt templates.
"""

INTENT_PROMPT = """分析用户问题，识别意图类型和提取关键信息。

用户问题：{user_query}
系统已配置的API列表：{api_list}

返回JSON格式：

1. intent_type: "api_query"(默认数据查询)|"data_detail"(明细)|"data_statistic"(统计)|"data_analysis"(分析)|"data_export"(导出)
2. entities: time_range(相对时间可自动计算)|trading_day_count|stock_symbol|market(US/CN/HK)|location|business|department|api_hint(建议API ID)
3. metrics: 指标名列表(如：订单量、销售额)
4. dimensions: 维度列表(如：日期、城市)
5. confidence: 置信度(0-1)
6. missing_info: 缺失信息列表(仅用户输入本身缺少必需参数时填写，相对时间和无可用API不算缺失；完整时返回null)
7. clarification_question: 有缺失时返回反问，否则返回null

完整查询示例：
{{"intent_type": "api_query", "entities": {{"time_range": {{"start": "2024-01-01", "end": "2024-01-07", "description": "最近7天"}}, "location": "北京", "api_hint": "sales"}}, "metrics": ["订单量"], "dimensions": ["日期"], "confidence": 0.95, "missing_info": null, "clarification_question": null}}

缺少时间范围：
{{"intent_type": "data_analysis", "entities": {{"stock_symbol": "AAPL", "market": "US", "api_hint": "stock_price"}}, "metrics": ["股价", "涨跌幅"], "dimensions": ["日期"], "confidence": 0.9, "missing_info": ["时间范围"], "clarification_question": "请问您想分析哪个时间范围的股价？例如：最近一周、本月或今年以来。"}}

缺少地点：
{{"intent_type": "api_query", "entities": {{"api_hint": "weather_api"}}, "metrics": ["天气"], "dimensions": [], "confidence": 0.9, "missing_info": ["地点"], "clarification_question": "请问您想查询哪个城市的天气？例如：北京、上海、广州。"}}

请只返回JSON，不要包含其他内容。"""

INTENT_CLARIFICATION_PROMPT = """用户问题不明确，请返回一个简短的澄清问题。

用户问题：{user_query}
当前识别结果：{current_intent}

请返回一个澄清问题："""


def get_intent_prompt(user_query: str, api_list: str = "", history: list = None) -> str:
    """Get intent recognition prompt with optional conversation history."""

    # Build conversation history section
    history_section = ""
    if history and len(history) > 0:
        # Format last 6 messages (3 rounds)
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

    return INTENT_PROMPT.format(user_query=user_query, api_list=api_list) + history_section


def get_clarification_prompt(user_query: str, current_intent: dict) -> str:
    """Get clarification prompt for ambiguous queries."""
    import json
    return INTENT_CLARIFICATION_PROMPT.format(
        user_query=user_query,
        current_intent=json.dumps(current_intent, ensure_ascii=False)
    )
