"""
Combined intent recognition + planning prompt templates.
Single LLM call for both intent understanding and execution planning.
"""

INTENT_PLANNER_PROMPT = """你是一个智能数据查询规划师。根据用户查询和可用数据源，完成两项任务：
1. 识别用户意图  2. 生成结构化执行计划

用户查询：{user_query}
可用API：{retrieved_apis}
可用数据库表：{retrieved_tables}
系统API列表（意图参考）：{api_list}

返回JSON，字段如下：
- intent_type: "api_query"|"data_detail"|"data_statistic"|"data_analysis"|"data_export"|"chitchat"
  · chitchat适用：打招呼、问候、闲聊、无数据分析需求的话语（如"你好""今天天气不错""帮我看看"等）
- direct_reply: 仅 intent_type="chitchat" 时填入可直接回复用户的友好短语；其他intent_type填null
- entities: {{time_range, stock_symbol, market, location, business, api_hint等}}
- metrics: 指标名列表 | dimensions: 维度列表 | confidence: 0~1
- missing_info: 缺失参数列表（相对时间如"最近N天"不算缺失，无相关API也不算）
- clarification_question: 缺失信息时的友好反问，信息完整则为null
- steps: 执行步骤，每项含 step_id, tool("api_fetch"|"sql_query"|"python_exec"), api_id(字符串), params, description, depends_on
  · intent_type="chitchat"时steps=[]，直接用direct_reply回复
- reasoning: 规划推理过程

【话题切换检测】当对话历史中出现与当前查询领域无关的新话题时（如从股票咨询切换到天气查询），忽略历史上下文，重新规划。

【闲聊快车道】用户话语属于闲聊/打招呼/无数据分析诉求时，intent_type设为"chitchat"，在direct_reply填入1-2句友好回复，steps=[]，跳过executor和analyzer。

【约束】无可用API时用sql_query；禁止虚构API；SQL表名/字段必须来自上方列表；python_exec禁止import

闲聊示例：
{{"intent_type":"chitchat","direct_reply":"你好！我是你的数据分析助手，可以帮你查询股票、天气、IP信息等。有什么我可以帮你的吗？","entities":{{}},"metrics":[],"dimensions":[],"confidence":1.0,"missing_info":null,"clarification_question":null,"steps":[],"reasoning":"用户打招呼，属于闲聊，直接回复"}}

话题切换示例：
用户历史：在聊股票（intent_type=api_query, entities.stock_symbol=AAPL）
用户新查询："北京今天多少度？"
→ 检测到话题切换（从股票→天气），忽略历史，重新规划天气查询

完整示例：
{{"intent_type":"api_query","entities":{{"stock_symbol":"AAPL","market":"US","time_range":{{"description":"最近7天"}},"api_hint":"stock_price"}},"metrics":["股价","涨跌幅"],"dimensions":["日期"],"confidence":0.95,"missing_info":null,"clarification_question":null,"steps":[{{"step_id":1,"tool":"api_fetch","api_id":"alpha_vantage_stock","params":{{"endpoint":"获取日线数据","params":{{"symbol":"AAPL","outputsize":"compact"}}}},"description":"获取苹果股票最近交易数据","depends_on":[]}}],"reasoning":"用户查询苹果股票，用股票API获取日线数据"}}

缺失信息示例：
{{"intent_type":"api_query","entities":{{"api_hint":"weather_api"}},"metrics":["天气"],"dimensions":[],"confidence":0.8,"missing_info":["地点"],"clarification_question":"请问您想查询哪个城市的天气？","steps":[],"reasoning":"缺少地点信息"}}

只返回JSON，不要包含其他内容。"""


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
        # 扩大历史窗口到 12 条，且只保留 role=user/assistant 且有 content 的消息
        filtered = [m for m in history[-12:] if m.get("role") in ("user", "assistant") and m.get("content")]
        history_lines = []
        for msg in filtered:
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
