"""
API Retrieval Node - 工具检索节点
从向量数据库召回 Top-K API Schema 并传递给下游节点
同时检索数据库表元数据用于 SQL 查询
"""
from typing import Dict, Any
from app.agent.state import AgentState
from app.services.api_retrieval_service import get_api_retrieval_service
from app.access.metadata.schema_loader import get_schema_loader
from app.access.database import get_mysql_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def retrieval_node(state: AgentState, permission=None) -> Dict[str, Any]:
    """
    API 检索节点：根据用户查询召回相关 API Schema 和数据库表

    Args:
        state: 当前 AgentState
        permission: 用户权限上下文

    Returns:
        包含 retrieved_apis 和 retrieved_tables 的字典
    """
    query = state.get("query", "")
    extracted_filters = state.get("extracted_filters") or {}
    intent_type = extracted_filters.get("intent_type", "")

    logger.info(f"[Retrieval Node] Processing query: {query}")
    logger.info(f"[Retrieval Node] Intent type: {intent_type}")

    # 获取用户ID
    user_id = permission.user_id if permission else "1"
    logger.info(f"[Retrieval Node] Using user_id: {user_id}")

    # 获取检索服务实例
    retrieval_service = get_api_retrieval_service()

    # 执行两阶段检索（向量召回 + LLM 精排）
    retrieved_apis = await retrieval_service.get_apis_for_query(
        query=query,
        user_id=user_id,
        top_k=10
    )

    logger.info(f"[Retrieval Node] Retrieved {len(retrieved_apis)} APIs")

    # 检索数据库表元数据
    retrieved_tables = []
    try:
        schema_loader = get_schema_loader()
        db_client = await get_mysql_client()
        await schema_loader.init(db_client)

        # 加载所有表的元数据
        db_metadata = await schema_loader.load_schema()

        # 将表元数据转换为类似 API 的格式供 Planner 使用
        for table_name, table_meta in db_metadata.tables.items():
            retrieved_tables.append({
                "config_id": f"table_{table_name}",
                "name": table_name,
                "description": table_meta.description or f"数据库表: {table_name}",
                "type": "sql_table",
                "schema": table_meta.to_schema_description()
            })

        logger.info(f"[Retrieval Node] Retrieved {len(retrieved_tables)} database tables")
    except Exception as e:
        logger.warning(f"[Retrieval Node] Failed to load table metadata: {e}")

    # 返回临时变量，不写入 AgentState
    return {
        "retrieved_apis": retrieved_apis,
        "retrieved_tables": retrieved_tables
    }
