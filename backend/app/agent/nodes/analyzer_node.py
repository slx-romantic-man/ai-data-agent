"""
Analyzer Node - 终局分析节点
从 data_context 提取所有累积数据并生成最终洞察
"""
from typing import Dict, Any, List
from app.agent.state import AgentState
from app.agent.core.data_analyzer import DataAnalyzer
from app.utils.logger import get_logger

logger = get_logger(__name__)


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
            # 检查是否有执行失败的步骤
            has_failures = any(
                isinstance(v, dict) and not v.get("success", True)
                for v in data_context.values()
            )
            if has_failures:
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
