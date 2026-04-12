"""
Analyzer Node - 终局分析节点
从 data_context 提取所有累积数据并生成最终洞察
"""
from typing import Dict, Any, List
from app.agent.state import AgentState
from app.agent.core.data_analyzer import DataAnalyzer
from app.utils.logger import get_logger

logger = get_logger(__name__)


def is_simple_query(plan: List[Dict[str, Any]], data: List[Dict[str, Any]]) -> bool:
    """
    判断查询是否为简单查询。

    简单查询定义：
    - 执行计划只有 1 步
    - 返回数据行数 ≤ 5

    满足以上两个条件的查询可跳过 Analyzer LLM 调用，
    直接用 Python 模板格式化为自然语言。
    """
    if not plan or not data:
        return False

    is_single_step = len(plan) == 1
    is_few_rows = len(data) <= 5

    logger.info(
        f"[is_simple_query] plan_steps={len(plan)}, data_rows={len(data)}, "
        f"single_step={is_single_step}, few_rows={is_few_rows}, "
        f"result={is_single_step and is_few_rows}"
    )
    return is_single_step and is_few_rows


def _format_simple_response(
    data: List[Dict[str, Any]],
    user_query: str,
) -> str:
    """
    将简单查询的 API 返回数据直接格式化为自然语言文本。

    不包含 JSON 原始数据或内部字段（_开头的字段）。
    输出为 Markdown 格式，加粗关键指标。

    Args:
        data: 数据行列表
        user_query: 用户原始查询

    Returns:
        格式化后的 Markdown 文本
    """
    if not data:
        return "抱歉，未查询到相关数据。"

    row = data[0]
    # Filter out internal fields (starting with _)
    visible_keys = [k for k in row.keys() if not k.startswith("_")]

    if not visible_keys:
        return "抱歉，查询结果不包含有效数据。"

    def format_value(value: Any, depth: int = 0) -> str:
        """Recursively format a value, handling nested dicts/lists."""
        if value is None or value == "":
            return "无"

        if isinstance(value, dict):
            sub_lines = []
            for sk, sv in value.items():
                sub_val = format_value(sv, depth + 1)
                sub_label = sk.replace("_", " ").replace("  ", " ").title()
                sub_lines.append(f"- **{sub_label}**: {sub_val}")
            return "\n" + "\n".join(sub_lines)

        if isinstance(value, list):
            items = []
            for item in value:
                formatted_item = format_value(item, depth + 1)
                items.append(f"  - {formatted_item}")
            return "\n" + "\n".join(items) if items else "空列表"

        if isinstance(value, float):
            if value == int(value):
                return str(int(value))
            return str(value)

        return str(value)

    lines = []
    for key in visible_keys:
        raw_value = row.get(key)
        label = key.replace("_", " ").replace("  ", " ").title()
        formatted = format_value(raw_value)
        lines.append(f"- **{label}**: {formatted}")

    summary = "\n".join(lines)
    return f"以下是您查询的结果：\n\n{summary}"


async def analyzer_node(state: AgentState) -> AgentState:
    """
    Analyzer Node: 综合分析所有数据并生成最终报告

    Args:
        state: 当前 AgentState

    Returns:
        更新后的 AgentState，包含分析报告追加到 messages
    """
    data_context = state.get("data_context", {})
    query = state.get("query", "")
    messages = state.get("messages", [])
    plan = state.get("plan", [])
    error = state.get("error")

    logger.info(
        f"[AnalyzerNode] Starting analysis with "
        f"{len(data_context)} data sources"
    )

    # 检查是否有明确的错误信息
    if error:
        logger.warning(f"[AnalyzerNode] Error detected: {error}")
        analysis_report = f"抱歉，无法完成您的请求。\n\n{error}"
    # 检查是否有权限错误（plan 为空但没有数据）
    elif not plan and not data_context:
        logger.warning("[AnalyzerNode] Empty plan and no data")
        analysis_report = (
            "抱歉，无法执行您的请求。\n\n"
            "可能的原因：\n"
            "• 您没有访问所需数据源或API的权限\n"
            "• 系统无法理解您的需求或生成执行计划\n"
            "• 所需的数据源暂时不可用\n\n"
            "建议：\n"
            "• 请确认您有相应的数据访问权限\n"
            "• 尝试更清晰地描述您的需求\n"
            "• 如问题持续，请联系管理员"
        )
    else:
        # 提取所有数据
        all_data = _extract_all_data(data_context)

        if not all_data:
            logger.warning("[AnalyzerNode] No data available for analysis")

            # 检查是否有API限流或其他错误
            error_messages = []
            for key, result in data_context.items():
                if isinstance(result, dict) and result.get("data"):
                    data = result["data"]
                    if isinstance(data, dict) and data.get("error"):
                        error_messages.append(data["error"])

            # 如果有API错误信息，优先显示
            if error_messages:
                error_text = error_messages[0]
                if "rate limit" in error_text.lower() or "requests per day" in error_text.lower():
                    analysis_report = (
                        "抱歉，API调用已达到每日限额。\n\n"
                        f"错误信息：{error_text}\n\n"
                        "建议：\n"
                        "• 请明天再试（API配额每日重置）\n"
                        "• 或联系管理员升级API计划"
                    )
                else:
                    analysis_report = (
                        f"抱歉，API调用失败：{error_text}\n\n"
                        "建议：\n"
                        "• 请稍后重试\n"
                        "• 如问题持续，请联系管理员"
                    )
            # 检查是否有执行失败的步骤
            elif any(isinstance(v, dict) and not v.get("success", True) for v in data_context.values()):
                analysis_report = (
                    "抱歉，数据查询过程中遇到问题，未能获取到有效数据。\n\n"
                    "可能的原因：\n"
                    "• 查询条件不匹配任何记录\n"
                    "• 数据源暂时不可用或响应超时\n"
                    "• 查询参数不正确\n\n"
                    "建议：\n"
                    "• 请检查查询条件是否正确\n"
                    "• 尝试调整时间范围或筛选条件\n"
                    "• 稍后重试"
                )
            else:
                analysis_report = (
                    "未查询到符合条件的数据。\n\n"
                    "建议：\n"
                    "• 请检查查询条件（如日期范围、代码、ID等）是否正确\n"
                    "• 尝试放宽筛选条件\n"
                    "• 确认数据源中是否存在相关记录"
                )
        else:
            # 简单查询跳过 Analyzer LLM 调用（F-01）
            if is_simple_query(plan, all_data):
                logger.info(
                    "[AnalyzerNode] Simple query detected, skipping LLM analysis"
                )
                analysis_report = _format_simple_response(all_data, query)
            else:
                # 使用 DataAnalyzer 生成洞察
                analyzer = DataAnalyzer()
                analysis_result = await analyzer.analyze(
                    data=all_data,
                    user_query=query,
                    analysis_type="summary"
                )
                analysis_report = analysis_result.get("analysis", "分析完成")

    # 追加分析报告到 messages
    messages.append({
        "role": "assistant",
        "content": analysis_report,
        "type": "analysis"
    })

    state["messages"] = messages
    logger.info("[AnalyzerNode] Analysis complete, report added to messages")

    return state


def _extract_all_data(data_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从 data_context 提取所有数据并合并

    Args:
        data_context: 数据上下文字典

    Returns:
        合并后的数据列表
    """
    all_data = []

    for key, result in data_context.items():
        if not isinstance(result, dict):
            logger.debug(f"[AnalyzerNode] Skipping {key}: not a dict")
            continue

        logger.debug(f"[AnalyzerNode] Processing {key}: success={result.get('success')}, has_data={bool(result.get('data'))}")

        if result.get("success") and result.get("data"):
            data = result["data"]
            logger.debug(f"[AnalyzerNode] Data type for {key}: {type(data)}, keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")

            # 处理规范化的股票数据格式
            if isinstance(data, dict) and "rows" in data:
                rows = data.get("rows", [])
                if isinstance(rows, list):
                    logger.info(f"[AnalyzerNode] Extracting {len(rows)} rows from {key}")
                    all_data.extend(rows)
            # 处理普通列表数据
            elif isinstance(data, list):
                all_data.extend(data)
            # 处理单个字典数据（包括Alpha Vantage原始响应）
            elif isinstance(data, dict):
                # 如果是Alpha Vantage的Time Series格式，展开为行
                if "Time Series (Daily)" in data:
                    time_series = data["Time Series (Daily)"]
                    for date, values in time_series.items():
                        row = {"date": date, **values}
                        all_data.append(row)
                    logger.info(f"[AnalyzerNode] Extracted {len(time_series)} time series rows from {key}")
                else:
                    all_data.append(data)

    logger.info(f"[AnalyzerNode] Extracted {len(all_data)} total rows from data_context")
    return all_data
