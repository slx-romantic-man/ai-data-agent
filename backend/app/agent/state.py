"""
AgentState 数据结构定义
用于 LangGraph 状态机的状态管理
"""
from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    """LangGraph Agent 状态定义"""

    # 对话消息历史
    messages: List[Dict[str, Any]]

    # 用户原始查询
    query: str

    # 意图澄清节点提取的过滤条件
    extracted_filters: Optional[Dict[str, Any]]

    # Planner 生成的执行计划
    plan: Optional[List[Dict[str, Any]]]

    # 当前执行到的步骤索引
    current_step: int

    # 数据上下文：存储各步骤查询结果
    # key 格式: step_{idx}_{api_id}
    data_context: Dict[str, Any]
