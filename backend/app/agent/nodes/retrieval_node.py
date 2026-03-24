"""
API Retrieval Node - 工具检索节点
从向量数据库召回 Top-K API Schema 并传递给下游节点
"""
from typing import Dict, Any
from app.agent.state import AgentState
from app.services.api_retrieval_service import get_api_retrieval_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    API 检索节点：根据用户查询召回相关 API Schema

    Args:
        state: 当前 AgentState

    Returns:
        包含 retrieved_apis 的字典（不污染 AgentState）
    """
    query = state.get("query", "")

    logger.info(f"[Retrieval Node] Processing query: {query}")

    # 获取检索服务实例
    retrieval_service = get_api_retrieval_service()

    # 执行两阶段检索（向量召回 + LLM 精排）
    # 默认返回 Top-10，user_id 暂时使用 "1"（后续从 state 获取）
    retrieved_apis = await retrieval_service.get_apis_for_query(
        query=query,
        user_id="1",
        top_k=10
    )

    logger.info(f"[Retrieval Node] Retrieved {len(retrieved_apis)} APIs")

    # 返回临时变量，不写入 AgentState
    return {"retrieved_apis": retrieved_apis}
