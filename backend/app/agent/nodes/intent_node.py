"""
Intent Clarification Node for LangGraph.
判断用户查询条件是否完备，如果缺失则返回反问，如果完备则提取过滤条件。
"""
import json
import re
from typing import Dict, Any
from app.agent.state import AgentState
from app.config.llm_config import get_llm
from app.agent.prompts.intent_prompt import get_intent_prompt
from app.agent.router.api_router import get_api_router
from app.utils.logger import get_logger

logger = get_logger()


async def intent_clarification_node(state: AgentState) -> AgentState:
    """
    Intent Clarification Node: 判断查询条件是否完备

    Args:
        state: 当前 AgentState

    Returns:
        更新后的 AgentState，包含 extracted_filters 或反问消息
    """
    query = state["query"]
    messages = state.get("messages", [])

    logger.info(f"[IntentNode] Processing query: {query}")
    logger.info(f"[IntentNode] Current messages count: {len(messages)}")

    # Check if this is a clarification follow-up (user responding to previous clarification question)
    is_clarification_followup = False
    if len(messages) >= 2:
        # Check if the last assistant message was a clarification question
        last_assistant_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                last_assistant_msg = msg
                break

        if last_assistant_msg and last_assistant_msg.get("type") == "clarification":
            is_clarification_followup = True
            logger.info(f"[IntentNode] Detected clarification follow-up. Previous question: {last_assistant_msg.get('content')}")

            # Merge query with history context
            merged_query = _merge_with_history(messages, query)
            logger.info(f"[IntentNode] Merged query: {merged_query}")
            query = merged_query  # Use merged query for intent analysis

    # 获取 API 列表描述
    try:
        api_router = get_api_router()
        api_list_desc = api_router.get_api_description_for_llm()
    except Exception:
        api_list_desc = "暂无已配置的API"

    # 调用 LLM 分析意图 (with conversation history)
    llm = get_llm()
    prompt = get_intent_prompt(query, api_list_desc, history=messages if is_clarification_followup else None)

    # Build chat messages for LLM
    llm_messages = [{"role": "system", "content": "你是一个专业的数据分析助手，擅长理解用户意图并判断查询条件是否完备。"}]
    if is_clarification_followup and messages:
        # Include conversation history for context
        llm_messages.extend(messages[-6:])  # Last 6 messages (3 rounds)
    llm_messages.append({"role": "user", "content": prompt})

    response = await llm.chat(llm_messages)

    # 解析 LLM 响应
    intent_data = _parse_llm_response(response)
    logger.info(f"[IntentNode] Parsed intent: {json.dumps(intent_data, ensure_ascii=False)}")

    # 检查是否有缺失信息
    missing_info = intent_data.get("missing_info")
    clarification_question = intent_data.get("clarification_question")

    if missing_info and clarification_question:
        # 条件不完备，返回反问
        logger.info(f"[IntentNode] Missing info detected: {missing_info}")
        state["messages"].append({
            "role": "assistant",
            "content": clarification_question,
            "type": "clarification"
        })
        state["extracted_filters"] = None
        return state

    # 条件完备，提取过滤条件
    extracted_filters = {
        "intent_type": intent_data.get("intent_type", "api_query"),
        "entities": intent_data.get("entities", {}),
        "metrics": intent_data.get("metrics", []),
        "dimensions": intent_data.get("dimensions", []),
        "confidence": intent_data.get("confidence", 0.8)
    }

    logger.info(f"[IntentNode] Extracted filters: {json.dumps(extracted_filters, ensure_ascii=False)}")
    state["extracted_filters"] = extracted_filters

    return state


def _parse_llm_response(response: str) -> Dict[str, Any]:
    """解析 LLM 响应提取 JSON"""
    try:
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        logger.error(f"[IntentNode] JSON parse error: {e}")

    return {
        "intent_type": "api_query",
        "entities": {},
        "metrics": [],
        "dimensions": [],
        "confidence": 0.5,
        "missing_info": None,
        "clarification_question": None
    }


def _merge_with_history(messages: list, current_query: str) -> str:
    """
    Merge current query with conversation history context.

    Args:
        messages: Conversation history
        current_query: Current user query

    Returns:
        Merged query string with context
    """
    # Extract previous user query from history
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
        # Merge: "previous query + clarification补充"
        merged = f"{previous_user_msg}，补充信息：{current_query}"
        logger.info(f"[IntentNode] Merged context: {merged}")
        return merged

    return current_query
