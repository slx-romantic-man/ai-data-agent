"""
Intent recognition prompt templates.
"""

INTENT_PROMPT = """分析用户问题，识别意图类型和提取关键信息。

用户问题：{user_query}

系统已配置的API列表：
{api_list}

请分析并返回以下信息（JSON格式）：

1. intent_type: 意图类型
   - "api_query": 调用API查询数据（默认类型，适用于大部分数据查询）
   - "data_detail": 查询数据明细（如：查看订单列表）
   - "data_statistic": 统计汇总（如：订单总量、平均值）
   - "data_analysis": 数据分析（如：趋势分析、对比分析）
   - "data_export": 导出数据（如：导出Excel）

2. entities: 提取的实体信息
   - time_range: 时间范围（如：最近7天、本月、2024年第一季度）
     注意：相对时间（最近N天、本周、本月、今年等）可以自动计算，不需要反问当前日期
   - trading_day_count: 交易日数量（如：最近7个交易日 → 7）
   - stock_symbol: 股票代码（如：苹果 → AAPL，特斯拉 → TSLA，阿里巴巴 → BABA）
   - market: 股票市场（如：美股 → US，A股 → CN，港股 → HK）
   - location: 地点（如：北京、上海）
   - business: 业务类型（如：外卖、到店）
   - department: 部门（如：销售部、技术部）
   - api_hint: 建议使用的API ID（根据问题内容推断，如：inventory、sales、employee、stock_price）

3. metrics: 指标名称列表
   - 如：订单量、销售额、用户数、转化率

4. dimensions: 维度列表
   - 如：日期、城市、业务线、渠道

5. confidence: 置信度（0-1之间）

6. missing_info: 缺失的关键信息列表（仅当用户输入本身缺少必需参数时才填写）
   - 例如："查询IP归属地"缺少具体IP地址 → ["IP地址"]
   - 例如："查看某订单详情"缺少订单号 → ["订单号"]
   - 注意：相对时间（最近N天、本周、本月等）不算缺失信息，系统可以自动计算
   - 注意：系统没有配置相关API不属于"缺失信息"，不应触发反问
   - 注意：用户查询的业务范围（统计、汇总类）只要有时间范围就算信息完整
   - 如果信息完整，必须返回null

7. clarification_question: 如果有缺失信息，生成友好的反问（如果信息完整则为null）
   - 例如："请提供需要查询的IP地址"
   - 例如："请提供订单号，或者指定要查询的时间范围"

返回格式示例：
{{
    "intent_type": "api_query",
    "entities": {{
        "time_range": {{"start": "2024-01-01", "end": "2024-01-07", "description": "最近7天"}},
        "location": "北京",
        "api_hint": "sales"
    }},
    "metrics": ["订单量"],
    "dimensions": ["日期"],
    "confidence": 0.95,
    "missing_info": null,
    "clarification_question": null
}}

股票查询示例：
{{
    "intent_type": "api_query",
    "entities": {{
        "stock_symbol": "AAPL",
        "market": "US",
        "trading_day_count": 7,
        "api_hint": "stock_price"
    }},
    "metrics": ["股价", "涨跌幅"],
    "dimensions": ["日期"],
    "confidence": 0.95,
    "missing_info": null,
    "clarification_question": null
}}

缺失信息示例：
{{
    "intent_type": "api_query",
    "entities": {{
        "api_hint": "geo"
    }},
    "metrics": [],
    "dimensions": [],
    "confidence": 0.8,
    "missing_info": ["IP地址"],
    "clarification_question": "请提供需要查询的IP地址"
}}

请只返回JSON，不要包含其他内容。"""

INTENT_CLARIFICATION_PROMPT = """用户问题的意图不明确，需要澄清。

用户问题：{user_query}
当前识别结果：{current_intent}

请生成一个澄清问题，帮助用户明确需求。

示例：
- "您是想查看数据明细还是统计汇总？"
- "请问您需要哪个时间范围的数据？"
- "您想分析哪个业务线的数据？"

请返回一个澄清问题："""

def get_intent_prompt(user_query: str, api_list: str = "") -> str:
    """Get intent recognition prompt."""
    return INTENT_PROMPT.format(user_query=user_query, api_list=api_list)

def get_clarification_prompt(user_query: str, current_intent: dict) -> str:
    """Get clarification prompt for ambiguous queries."""
    import json
    return INTENT_CLARIFICATION_PROMPT.format(
        user_query=user_query,
        current_intent=json.dumps(current_intent, ensure_ascii=False)
    )