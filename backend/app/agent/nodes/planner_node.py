"""
Planner Node - 全局规划师节点
根据用户查询和检索到的API生成结构化执行计划
"""
import json
import re
from typing import Dict, Any
from pydantic import BaseModel, Field, ValidationError
from app.agent.state import AgentState
from app.config.llm_config import get_llm
from app.agent.prompts.planner_prompt import get_planner_prompt
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PlanStep(BaseModel):
    """执行步骤模型"""
    step_id: int = Field(..., description="步骤编号")
    tool: str = Field(..., description="工具类型: api_fetch, sql_query 或 python_exec")
    api_id: str = Field(default="", description="API标识符")
    params: Dict[str, Any] = Field(default_factory=dict, description="调用参数")
    description: str = Field(..., description="步骤描述")
    depends_on: list = Field(default_factory=list, description="依赖的前置步骤ID")


class ExecutionPlan(BaseModel):
    """执行计划模型"""
    steps: list[PlanStep] = Field(..., description="执行步骤列表")
    reasoning: str = Field(..., description="规划推理过程")


async def planner_node(state: AgentState, retrieved_apis: list, retrieved_tables: list = None) -> AgentState:
    """
    Planner Node: 生成结构化执行计划

    Args:
        state: 当前 AgentState
        retrieved_apis: 从 retrieval_node 传递的 API 列表
        retrieved_tables: 从 retrieval_node 传递的数据库表列表

    Returns:
        更新后的 AgentState，包含 plan 字段
    """
    query = state["query"]
    extracted_filters = state.get("extracted_filters") or {}
    retrieved_tables = retrieved_tables or []

    logger.info(f"[PlannerNode] Generating plan for query: {query}")
    logger.info(f"[PlannerNode] Available APIs: {len(retrieved_apis)}, Tables: {len(retrieved_tables)}")

    # 合并 API 和表信息
    all_tools = retrieved_apis + retrieved_tables

    # 调用 LLM 生成计划
    llm = get_llm()
    prompt = get_planner_prompt(query, extracted_filters, all_tools)

    logger.info(f"[PlannerNode] Prompt sent to LLM:\n{prompt[:2000]}")

    response = await llm.chat([
        {"role": "system", "content": "你是一个专业的数据查询规划师，擅长将复杂查询拆解为结构化的执行步骤。"},
        {"role": "user", "content": prompt}
    ])

    logger.info(f"[PlannerNode] LLM Response: {response[:1000]}")

    # 解析并验证计划
    plan_data = _parse_and_validate_plan(response)

    if not plan_data:
        logger.warning("[PlannerNode] LLM plan parsing failed, attempting fallback")
        plan_data = _create_fallback_plan(query, retrieved_apis)

    # 校验计划有效性
    if not plan_data:
        logger.error("[PlannerNode] Cannot generate valid plan - insufficient metadata or no tools available")
        state["plan"] = []
        state["error"] = "无法生成有效的执行计划。可能原因：没有找到合适的API或数据源，或API元数据不完整。"
        state["current_step"] = 0
        return state

    logger.info(f"[PlannerNode] Generated plan with {len(plan_data)} steps")

    # 更新状态
    state["plan"] = plan_data
    state["current_step"] = 0

    return state


def _parse_and_validate_plan(response: str) -> list:
    """解析并验证 LLM 响应的执行计划"""
    try:
        # 提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            logger.error("[PlannerNode] No JSON found in response")
            return None

        plan_dict = json.loads(json_match.group())

        # 强制转换 api_id 为字符串（修复类型错误）
        if "steps" in plan_dict:
            for step in plan_dict["steps"]:
                if "api_id" in step and step["api_id"] is not None:
                    step["api_id"] = str(step["api_id"])

        # Pydantic 验证
        execution_plan = ExecutionPlan(**plan_dict)

        # 转换为字典列表
        return [step.model_dump() for step in execution_plan.steps]

    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"[PlannerNode] Validation error: {e}")
        return None


def _create_fallback_plan(query: str, retrieved_apis: list) -> list:
    """
    创建降级计划（当LLM生成失败时）

    安全原则：
    1. 禁止生成 unknown 的 api_id 或存储 key
    2. 必须基于可信的 API 元数据
    3. 若元数据不足，返回空计划（由调用方处理失败）
    """
    if not retrieved_apis:
        logger.warning("[PlannerNode] Fallback: No APIs available, cannot generate plan")
        return []

    # 使用第一个检索到的API创建简单计划
    first_api = retrieved_apis[0]

    # 严格验证：必须有 config_id，禁止使用 unknown
    api_identifier = first_api.get("config_id")
    if not api_identifier:
        logger.error("[PlannerNode] Fallback: API missing config_id, cannot generate safe plan")
        return []

    # 验证 api_identifier 不包含 unknown
    if "unknown" in str(api_identifier).lower():
        logger.error(f"[PlannerNode] Fallback: Invalid api_id '{api_identifier}', refusing to generate plan")
        return []

    logger.info(f"[PlannerNode] Fallback: Generating minimal plan with API '{api_identifier}'")

    return [{
        "step_id": 1,
        "tool": "api_fetch",
        "api_id": api_identifier,
        "params": {},
        "description": f"查询 {first_api.get('description', 'data')}",
        "depends_on": []
    }]
