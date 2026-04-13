"""
Combined Intent + Planner Node - Single LLM call for both intent recognition and execution planning.
"""
import json
import re
from typing import Dict, Any, List
from pydantic import BaseModel, Field, ValidationError
from app.agent.state import AgentState
from app.config.llm_config import get_llm
from app.agent.prompts.intent_planner_prompt import get_intent_planner_prompt
from app.agent.router.api_router import get_api_router
from app.utils.llm_cache import get_llm_cache
from app.utils.logger import get_logger

logger = get_logger()


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


async def intent_planner_node(state: AgentState, retrieved_apis: list, retrieved_tables: list = None) -> AgentState:
    """
    Combined Intent + Planner Node: 识别意图并生成执行计划（单次LLM调用）

    Args:
        state: 当前 AgentState
        retrieved_apis: 从 retrieval_node 传递的 API 列表
        retrieved_tables: 从 retrieval_node 传递的数据库表列表

    Returns:
        更新后的 AgentState，包含 extracted_filters 或反问消息，以及 plan 字段
    """
    query = state["query"]
    messages = state.get("messages", [])
    retrieved_tables = retrieved_tables or []

    logger.info(f"[IntentPlannerNode] Processing query: {query}")
    logger.info(f"[IntentPlannerNode] Available APIs: {len(retrieved_apis)}, Tables: {len(retrieved_tables)}")

    # Check if this is a clarification follow-up
    is_clarification_followup = False
    if len(messages) >= 2:
        last_assistant_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                last_assistant_msg = msg
                break

        if last_assistant_msg and last_assistant_msg.get("type") == "clarification":
            is_clarification_followup = True
            logger.info(f"[IntentPlannerNode] Detected clarification follow-up. Previous question: {last_assistant_msg.get('content')}")
            merged_query = _merge_with_history(messages, query)
            logger.info(f"[IntentPlannerNode] Merged query: {merged_query}")
            query = merged_query
            state["query"] = merged_query

    # 获取 API 列表描述
    try:
        api_router = get_api_router()
        api_list_desc = api_router.get_api_description_for_llm()
    except Exception:
        api_list_desc = "暂无已配置的API"

    # 合并 API 和表信息
    all_tools = retrieved_apis + retrieved_tables

    # 调用 LLM 生成意图 + 计划（单次调用）
    llm = get_llm()
    prompt = get_intent_planner_prompt(
        user_query=query,
        retrieved_apis=all_tools,
        retrieved_tables=retrieved_tables,
        api_list=api_list_desc,
        history=messages if is_clarification_followup else None
    )

    llm_messages = [{"role": "system", "content": "你是一个专业的数据查询规划师，擅长理解用户意图并生成结构化的执行计划。"}]
    if is_clarification_followup and messages:
        llm_messages.extend(messages[-6:])
    llm_messages.append({"role": "user", "content": prompt})

    # Check cache first
    cache = get_llm_cache()
    cached_response = cache.get(llm_messages)
    if cached_response is not None:
        logger.info(f"[IntentPlannerNode] Cache hit for query: {query}")
        response = cached_response
    else:
        response = await llm.chat(llm_messages, max_tokens=1024)
        cache.set(llm_messages, response)

    logger.info(f"[IntentPlannerNode] LLM Response: {response[:1000]}")

    # 解析 LLM 响应
    result_data = _parse_llm_response(response)
    logger.info(f"[IntentPlannerNode] Parsed result: {json.dumps(result_data, ensure_ascii=False)[:500]}")

    # 检查是否有缺失信息
    missing_info = result_data.get("missing_info")
    clarification_question = result_data.get("clarification_question")

    if missing_info and clarification_question:
        # 条件不完备，返回反问
        logger.info(f"[IntentPlannerNode] Missing info detected: {missing_info}")
        state["messages"].append({
            "role": "assistant",
            "content": clarification_question,
            "type": "clarification"
        })
        state["extracted_filters"] = None
        state["plan"] = []
        return state

    # 条件完备，提取过滤条件
    extracted_filters = {
        "intent_type": result_data.get("intent_type", "api_query"),
        "entities": result_data.get("entities", {}),
        "metrics": result_data.get("metrics", []),
        "dimensions": result_data.get("dimensions", []),
        "confidence": result_data.get("confidence", 0.8)
    }

    logger.info(f"[IntentPlannerNode] Extracted filters: {json.dumps(extracted_filters, ensure_ascii=False)}")
    state["extracted_filters"] = extracted_filters

    # 解析并验证执行计划
    steps = result_data.get("steps", [])
    if steps:
        plan_data = _parse_and_validate_plan(steps)
        if not plan_data:
            logger.warning("[IntentPlannerNode] LLM plan parsing failed, attempting fallback")
            plan_data = _create_fallback_plan(query, retrieved_apis)

        if not plan_data:
            logger.error("[IntentPlannerNode] Cannot generate valid plan")
            state["plan"] = []
            state["error"] = "无法生成有效的执行计划。可能原因：没有找到合适的API或数据源，或API元数据不完整。"
            state["current_step"] = 0
            return state

        logger.info(f"[IntentPlannerNode] Generated plan with {len(plan_data)} steps")
        state["plan"] = plan_data
    else:
        # 没有步骤（可能是信息不完整或无需执行）
        state["plan"] = []

    state["current_step"] = 0
    return state


def _parse_llm_response(response: str) -> Dict[str, Any]:
    """解析 LLM 响应提取 JSON"""
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.error(f"[IntentPlannerNode] JSON parse error: {e}")

    return {
        "intent_type": "api_query",
        "entities": {},
        "metrics": [],
        "dimensions": [],
        "confidence": 0.5,
        "missing_info": None,
        "clarification_question": None,
        "steps": [],
        "reasoning": ""
    }


def _parse_and_validate_plan(steps: list) -> list:
    """解析并验证执行计划"""
    try:
        # 强制转换 api_id 为字符串
        for step in steps:
            if "api_id" in step and step["api_id"] is not None:
                step["api_id"] = str(step["api_id"])

        execution_plan = ExecutionPlan(steps=steps, reasoning="")
        return [step.model_dump() for step in execution_plan.steps]
    except (ValidationError, Exception) as e:
        logger.error(f"[IntentPlannerNode] Plan validation error: {e}")
        return None


def _create_fallback_plan(query: str, retrieved_apis: list) -> list:
    """
    创建降级计划（当LLM生成失败时）

    安全原则：
    1. 禁止生成 unknown 的 api_id 或存储 key
    2. 必须基于可信的 API 元数据
    3. 若元数据不足，返回空计划
    """
    if not retrieved_apis:
        logger.warning("[IntentPlannerNode] Fallback: No APIs available, cannot generate plan")
        return []

    first_api = retrieved_apis[0]
    api_identifier = first_api.get("config_id")
    if not api_identifier:
        logger.error("[IntentPlannerNode] Fallback: API missing config_id, cannot generate safe plan")
        return []

    if "unknown" in str(api_identifier).lower():
        logger.error(f"[IntentPlannerNode] Fallback: Invalid api_id '{api_identifier}', refusing to generate plan")
        return []

    endpoints = first_api.get("endpoints", {})
    if not endpoints:
        logger.error(f"[IntentPlannerNode] Fallback: API '{api_identifier}' has no endpoints, cannot generate plan")
        return []

    first_endpoint_name = list(endpoints.keys())[0]
    first_endpoint = endpoints[first_endpoint_name]

    logger.info(f"[IntentPlannerNode] Fallback: Generating minimal plan with API '{api_identifier}', endpoint '{first_endpoint_name}'")

    params = {
        "endpoint": first_endpoint_name,
        "params": first_endpoint.get("params_mapping", {})
    }

    return [{
        "step_id": 1,
        "tool": "api_fetch",
        "api_id": api_identifier,
        "params": params,
        "description": f"查询 {first_api.get('description', 'data')}",
        "depends_on": []
    }]


def _merge_with_history(messages: list, current_query: str) -> str:
    """
    Merge current query with conversation history context.
    """
    previous_user_msg = None
    previous_assistant_msg = None

    for msg in reversed(messages):
        if msg.get("role") == "user" and msg.get("content") != current_query:
            previous_user_msg = msg.get("content")
        elif msg.get("role") == "assistant" and msg.get("type") == "clarification":
            previous_assistant_msg = msg.get("content")

        if previous_user_msg and previous_assistant_msg:
            break

    if previous_user_msg:
        merged = f"{previous_user_msg}，补充信息：{current_query}"
        logger.info(f"[IntentPlannerNode] Merged context: {merged}")
        return merged

    return current_query
