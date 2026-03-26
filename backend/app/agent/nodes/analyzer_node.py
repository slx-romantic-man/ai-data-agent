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

    logger.info(
        f"[AnalyzerNode] Starting analysis with "
        f"{len(data_context)} data sources"
    )

    # 检查是否有权限错误（plan 为空但没有数据）
    if not plan and not data_context:
        logger.warning("[AnalyzerNode] Empty plan, checking for errors")
        # 这可能是权限检查失败导致的
        analysis_report = (
            "抱歉，无法执行您的请求。可能的原因：\n"
            "1. 您没有访问所需 API 的权限，请联系管理员授权\n"
            "2. 系统无法生成有效的执行计划\n\n"
            "请检查您的权限设置或重新描述您的需求。"
        )
    else:
        # 提取所有数据
        all_data = _extract_all_data(data_context)

        if not all_data:
            logger.warning("[AnalyzerNode] No data available for analysis")
            analysis_report = "未能获取到有效数据进行分析。"
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
            continue

        if result.get("success") and result.get("data"):
            data = result["data"]
            if isinstance(data, list):
                all_data.extend(data)
            elif isinstance(data, dict):
                all_data.append(data)

    logger.info(f"[AnalyzerNode] Extracted {len(all_data)} total rows from data_context")
    return all_data
