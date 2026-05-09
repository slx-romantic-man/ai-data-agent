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

    # 规划阶段生成的可展示推理说明
    planning_reasoning: Optional[str]

    # 当前执行到的步骤索引
    current_step: int

    # 检索到的API和数据库表列表（从 retrieval 传递到 intent_planner）
    retrieved_apis: Optional[List[Dict[str, Any]]]
    retrieved_tables: Optional[List[Dict[str, Any]]]

    # 数据上下文：存储各步骤查询结果
    # key 格式: step_{idx}_{api_id}
    data_context: Dict[str, Any]

    # 是否需要人工审批
    requires_approval: bool

    # 已完成步骤的 step_id 列表（用于并行执行依赖追踪）
    completed_step_ids: list
