"""
Chat API endpoints.
"""
from typing import Dict, Any, AsyncIterator, List
import json
import os
import asyncio
from datetime import datetime, date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    AgentResponse,
    DataResult,
    IntentType,
    ReasoningLog,
    ConversationContext,
    ConversationState,
)
from app.models.user import UserContext
from app.agent.core.streaming_agent import get_streaming_agent
from app.api.dependencies import get_user_context, get_permission_context
from app.models.permission import PermissionContext
from app.agent.graph import create_graph
from app.agent.state import AgentState
from app.agent.nodes.analyzer_node import run_analyzer_stream
from app.access.database import get_mysql_client, get_postgres_client
from app.access.metadata import get_schema_loader
from app.config.settings import settings
from app.config.llm_config import get_llm
from app.utils.logger import get_logger
from app.utils.helpers import generate_session_id
from app.services.user_service import get_user_service
from app.services.credit_service import get_credit_service
from app.services.conversation_service import get_conversation_service
from app.services.suggestion_service import get_suggestion_service


class _DateEncoder(json.JSONEncoder):
    """JSON encoder that handles date, datetime, and Decimal types."""

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _json_dumps(obj, **kwargs) -> str:
    """json.dumps wrapper with date/Decimal support."""
    return json.dumps(obj, cls=_DateEncoder, **kwargs)


router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger()

# Persistent session storage
SESSION_FILE = "sessions.json"
_sessions: Dict[str, Any] = {}


@router.get("/suggestions")
async def get_suggestions(
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """
    Get smart question suggestions based on user's APIs and chat history.
    Respects admin/employee permission isolation — non-admin users only see
    APIs they have been explicitly granted permission for.
    """
    suggestion_service = get_suggestion_service()
    suggestions = await suggestion_service.get_suggestions(user.user_id)
    return {
        "suggestions": suggestions,
        "total": len(suggestions)
    }


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def _load_sessions():
    """Load sessions from file."""
    global _sessions
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                _sessions = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            # If load fails (e.g. corrupted JSON), start with empty sessions
            _sessions = {}
            # Move corrupted file to backup
            try:
                os.rename(SESSION_FILE, f"{SESSION_FILE}.bak")
                logger.info(f"Corrupted {SESSION_FILE} moved to backup.")
            except Exception:
                pass


def _save_sessions():
    """Save sessions to file."""
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(
                _sessions,
                f,
                ensure_ascii=False,
                indent=2,
                cls=DateTimeEncoder
            )
    except Exception as e:
        logger.error(f"Failed to save sessions: {e}")


# Initialize sessions on startup
_load_sessions()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: UserContext = Depends(get_user_context),
    permission: PermissionContext = Depends(get_permission_context),
) -> ChatResponse:
    """
    Process a chat message and return AI response.

    -1. **优先参考历史**：在追问时优先使用历史上下文中的数据。
2. **保持约束一致性**：继续沿用之前对话限定的时间范围约束。
3. **逻辑连贯性**：结论不得与之前已确认的事实相矛盾。
    """
    try:
        # Override user context if user_id provided in request
        if request.user_id:
            user_service = get_user_service()
            override_user = user_service.get_user_context(request.user_id)
            if override_user:
                user = override_user
                from app.access.permission import get_rbac_manager
                rbac_manager = get_rbac_manager()
                permission = rbac_manager.build_permission_context(
                    user_id=user.user_id,
                    role=user.role,
                    department=user.department,
                    business_line=user.business_line,
                )

        # Get or create session
        session_id = request.session_id or generate_session_id()

        # Get session history
        session = _sessions.get(session_id, {
            "messages": [],
            "created_at": datetime.now(),
        })

        # Format conversation history for LangGraph (preserve type metadata for clarification detection)
        conversation_history = session.get("messages", [])
        formatted_history = []
        for msg in conversation_history:
            formatted_msg = {
                "role": msg["role"],
                "content": msg["content"]
            }
            # Preserve "type" field for clarification detection (e.g., "type": "clarification")
            if "type" in msg:
                formatted_msg["type"] = msg["type"]
            formatted_history.append(formatted_msg)

        logger.info(f"[ChatAPI] Loaded {len(formatted_history)} history messages for session {session_id}")

        # Use LangGraph workflow
        graph = await create_graph(permission)

        initial_state: AgentState = {
            "messages": formatted_history,  # Load conversation history
            "query": request.message,
            "extracted_filters": None,
            "plan": None,
            "current_step": 0,
            "data_context": {}
        }

        config = {"configurable": {"thread_id": session_id}}
        result = await graph.ainvoke(initial_state, config)

        # Extract results
        messages = result.get("messages", [])
        if messages:
            last_msg = messages[-1]
            final_answer_text = last_msg.get("content") if isinstance(last_msg, dict) else last_msg.content
        else:
            final_answer_text = "处理完成"

        data_context = result.get("data_context", {})
        final_data = None
        final_sql = ""

        # Extract SQL and data from data_context
        for key, value in data_context.items():
            if isinstance(value, dict):
                if "sql" in value:
                    final_sql = value.get("sql", "")
                if "data" in value:
                    final_data = value.get("data")

        final_reasoning_log = None

        # Update session: Add user message and new assistant response
        # Step 1: Add user's current request to session (CRITICAL for clarification detection)
        user_msg = {
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        }
        session["messages"].append(user_msg)

        # Step 2: Add only the NEW assistant response (last message from LangGraph)
        # LangGraph messages list contains entire conversation history, we only need the new response
        if messages:
            last_msg = messages[-1]  # Get only the last (new) message

            if isinstance(last_msg, dict):
                # Only process assistant messages
                if last_msg.get("role") == "assistant":
                    msg_content = last_msg.get("content", "")

                    # Preserve all message fields including type
                    session_msg = {
                        "role": "assistant",
                        "content": msg_content,
                        "timestamp": datetime.now().isoformat()
                    }
                    # Preserve metadata fields like "type" for clarification detection
                    if "type" in last_msg:
                        session_msg["type"] = last_msg["type"]

                    session["messages"].append(session_msg)
            else:
                # Handle LangChain message objects (only assistant)
                if hasattr(last_msg, 'type') and last_msg.type in ["assistant", "ai"]:
                    # Check if it's a clarification by analyzing content
                    msg_content = last_msg.content
                    session_msg = {
                        "role": "assistant",
                        "content": msg_content,
                        "timestamp": datetime.now().isoformat()
                    }
                    # Detect clarification from LangChain AIMessage
                    if hasattr(last_msg, 'additional_kwargs') and 'type' in last_msg.additional_kwargs:
                        session_msg["type"] = last_msg.additional_kwargs['type']
                    session["messages"].append(session_msg)

        session["updated_at"] = datetime.now()
        _sessions[session_id] = session
        _save_sessions()

        data_result = None
        if final_data:
            data_result = DataResult(
                columns=final_data.get("columns", []),
                rows=final_data.get("rows", []),
                total=final_data.get("total"),
            )

        reasoning_log_obj = None
        if isinstance(final_reasoning_log, dict):
            try:
                reasoning_log_obj = ReasoningLog.model_validate(final_reasoning_log)
            except Exception:
                reasoning_log_obj = None

        response = AgentResponse(
            text=final_answer_text,
            data=data_result,
            sql=final_sql,
            intent=IntentType.API_QUERY,
            reasoning_log=reasoning_log_obj,
        )

        # Build response
        excel_url = None
        if response.data:
            excel_url = f"/api/v1/export/{session_id}.xlsx"

        return ChatResponse(
            session_id=session_id,
            response=response,
            excel_url=excel_url,
        )

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}",
        )


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """Get session history."""
    if session_id not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return _sessions[session_id]


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: UserContext = Depends(get_user_context),
) -> Dict[str, str]:
    """Delete a session."""
    if session_id in _sessions:
        del _sessions[session_id]

    return {"status": "deleted", "session_id": session_id}


@router.get("/history")
async def get_history(
    limit: int = 10,
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """Get user's chat history."""
    user_sessions = [
        {"session_id": sid, **s}
        for sid, s in _sessions.items()
    ]

    # Sort by updated_at
    user_sessions.sort(
        key=lambda x: x.get("updated_at", x.get("created_at")),
        reverse=True,
    )

    return {
        "sessions": user_sessions[:limit],
        "total": len(user_sessions),
    }


@router.get("/debug/schema")
async def debug_schema(
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """
    Debug endpoint to view database schema.
    Shows all tables and columns that the agent can see.
    """
    try:
        # Get database client based on database type
        if "mysql" in settings.DATABASE_URL.lower():
            db_client = await get_mysql_client()
        else:
            db_client = await get_postgres_client()

        # Get all tables
        tables = await db_client.get_all_tables()

        # Get schema loader
        schema_loader = get_schema_loader()
        await schema_loader.init(db_client)

        # Load schema
        return {
            "database_type": (
                "mysql" if "mysql" in settings.DATABASE_URL.lower() 
                else "postgresql"
            ),
            "table_count": len(tables),
            "tables": tables,
            "schema_description": schema_loader.get_schema_description(),
        }
    except Exception as e:
        logger.error(f"Debug schema error: {str(e)}")
        return {
            "error": str(e),
            "database_url": (
                settings.DATABASE_URL.split("@")[-1] 
                if "@" in settings.DATABASE_URL else "configured"
            ),
        }


@router.get("/debug/tables/{table_name}")
async def debug_table(
    table_name: str,
    limit: int = 10,
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """
    Debug endpoint to view table data.
    """
    try:
        if "mysql" in settings.DATABASE_URL.lower():
            db_client = await get_mysql_client()
        else:
            db_client = await get_postgres_client()

        # Get table schema
        columns = await db_client.get_table_columns(table_name)

        # Get sample data
        sample_sql = f"SELECT * FROM {table_name} LIMIT {limit}"
        sample_data = await db_client.execute_safe_query(sample_sql)

        return {
            "table_name": table_name,
            "columns": columns,
            "row_count": sample_data.get("row_count", 0),
            "sample_data": sample_data.get("data", []),
        }
    except Exception as e:
        logger.error(f"Debug table error: {str(e)}")
        return {"error": str(e)}


@router.get("/debug/llm")
async def debug_llm(
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """
    Debug endpoint to test LLM connection.
    """
    try:
        llm = get_llm()

        # Simple test message
        test_message = "你好，请回复'测试成功'"
        response = await llm.chat([
            {"role": "user", "content": test_message}
        ])

        return {
            "success": True,
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_MODEL,
            "api_base": settings.LLM_API_BASE,
            "test_message": test_message,
            "response": response,
        }
    except Exception as e:
        logger.error(f"LLM test error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_MODEL,
            "api_base": settings.LLM_API_BASE,
        }


@router.post("/simple")
async def simple_chat(
    request: ChatRequest,
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """
    Simple chat endpoint for testing - bypasses agent engine.
    """
    try:
        llm = get_llm()

        # Direct LLM call
        response = await llm.chat([
            {"role": "system", "content": "你是一个数据分析助手。"},
            {"role": "user", "content": request.message}
        ])

        return {
            "success": True,
            "session_id": request.session_id or generate_session_id(),
            "response": response,
        }
    except Exception as e:
        logger.error(f"Simple chat error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }


@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    user: UserContext = Depends(get_user_context),
    permission: PermissionContext = Depends(get_permission_context),
):
    """
    Streaming chat endpoint with real-time reasoning output.
    Uses Server-Sent Events (SSE) to stream each reasoning step.

    Event types:
    - start: Query processing started
    - thought: Agent's thought process (may be partial)
    - action: Action being executed
    - executing: Tool execution started
    - observation: Tool execution result
    - answer: Final answer text
    - data: Data results (table)
    - done: Processing complete
    - error: Error occurred
    - quota: Quota information after deduction
    """
    async def event_generator():
        def _sse(event_type: str, data: Dict[str, Any] | None = None) -> str:
            return f"data: {_json_dumps({'type': event_type, 'data': data or {}}, ensure_ascii=False)}\n\n"

        async def _stream_text(text: str, chunk_size: int = 8):
            normalized = text or ""
            for index in range(0, len(normalized), chunk_size):
                yield _sse("streaming_text", {"content": normalized[index:index + chunk_size]})

        def _build_plan_thought(
            plan: list,
            planning_reasoning: str,
            extracted_filters: Dict[str, Any] | None,
        ) -> str:
            if planning_reasoning:
                return planning_reasoning

            intent_type = (extracted_filters or {}).get("intent_type", "api_query")
            if not plan:
                return f"我已经识别出当前问题属于 {intent_type}，但还需要进一步确认结果该如何返回。"

            step_descriptions = [
                step.get("description", f"步骤 {idx + 1}")
                for idx, step in enumerate(plan[:3])
            ]
            suffix = "，然后继续后续处理。" if len(plan) > 3 else "。"
            return (
                f"我已经识别出当前问题属于 {intent_type}，"
                f"接下来会按顺序执行：{'；'.join(step_descriptions)}{suffix}"
            )

        def _build_action_payload(step: Dict[str, Any]) -> Dict[str, Any]:
            params = step.get("params", {})
            return {
                "tool": step.get("tool", "unknown"),
                "name": step.get("description", ""),
                "parameters": params,
            }

        def _count_rows(raw_data: Any) -> int:
            if isinstance(raw_data, dict) and "rows" in raw_data:
                rows = raw_data.get("rows", [])
                return len(rows) if isinstance(rows, list) else 0
            if isinstance(raw_data, list):
                return len(raw_data)
            if isinstance(raw_data, dict):
                return 1
            return 0

        def _summarize_execution_result(result: Dict[str, Any] | None) -> str:
            if not isinstance(result, dict):
                return "执行完成。"

            if result.get("success"):
                row_count = _count_rows(result.get("data"))
                if row_count > 0:
                    return f"执行成功，获取到 {row_count} 条数据。"
                return "执行成功，已拿到结果。"

            error_message = result.get("error")
            if error_message:
                return f"执行失败：{error_message}"
            return "执行结束，但没有返回可用结果。"

        try:
            # Get services
            user_service = get_user_service()
            credit_service = get_credit_service()
            conversation_service = get_conversation_service()

            # Get user account for credit check
            user_account = user_service.get_user_by_user_id(user.user_id)
            if not user_account:
                yield _sse("error", {"message": "用户不存在"})
                return

            # Check quota (skip for admin)
            if not user_account.has_unlimited_credits():
                user_service.check_and_reset_if_needed(user.user_id)
                if user_account.quota.current_balance <= 0:
                    yield _sse("error", {
                        "message": "积分不足，请等待每日重置或联系管理员充值",
                        "quota": {
                            "current_balance": user_account.quota.current_balance,
                            "daily_limit": user_account.quota.daily_limit,
                        },
                    })
                    return

            # Get or create session
            session_id = request.session_id or generate_session_id()
            session_messages = []
            if session_id and session_id in _sessions:
                session_messages = _sessions[session_id].get("messages", [])

            # Format conversation history for LangGraph (remove timestamp and extra fields)
            conversation_history = session_messages
            formatted_history = []
            for msg in conversation_history:
                formatted_msg = {
                    "role": msg["role"],
                    "content": msg["content"]
                }
                # Preserve "type" field for clarification detection
                if "type" in msg:
                    formatted_msg["type"] = msg["type"]
                formatted_history.append(formatted_msg)

            # Check if waiting for missing info
            user_message = request.message
            context = conversation_service.get_context(user.user_id, session_id)
            if context and context.state == ConversationState.WAITING_FOR_INFO:
                # User is providing missing info, merge with original query
                logger.info(f"Merging user input with pending query: {context.pending_query}")
                user_message = f"{context.pending_query}\n补充信息: {request.message}"
                # Clear context after merging
                conversation_service.clear_context(user.user_id, session_id)

            # Track final answer for session storage
            final_answer_text = ""
            final_data = None
            total_tokens = 0
            is_clarification = False  # Track if response is a clarification
            next_reasoning_step = 0
            seen_completed_step_ids = set()
            execution_step_numbers: Dict[int, int] = {}
            plan_by_step_id: Dict[int, tuple[int, Dict[str, Any]]] = {}
            # F-23: Collect all thought events for persistence
            thought_events: List[Dict[str, Any]] = []

            def _emit_thought(step: int, content: str):
                """Yield a thought SSE event and also append to thought_events list for persistence."""
                thought_events.append({"step": step, "content": content})
                return _sse("thought", {"step": step, "content": content})

            def allocate_reasoning_step() -> int:
                nonlocal next_reasoning_step
                next_reasoning_step += 1
                return next_reasoning_step

            # Create LangGraph workflow
            graph = await create_graph(permission)

            # Initialize state
            initial_state: AgentState = {
                "messages": formatted_history,
                "query": user_message,
                "extracted_filters": None,
                "plan": None,
                "planning_reasoning": None,
                "current_step": 0,
                "data_context": {}
            }

            # Stream events from LangGraph
            config = {"configurable": {"thread_id": session_id}}

            # Phase 1: Run graph with interrupt_before=["analyzer"] to stop before analyzer
            async for event in graph.astream(
                initial_state, config, stream_mode="updates",
                interrupt_before=["analyzer"],
            ):
                for node_name, node_output in event.items():
                    # Skip internal LangGraph interrupt events
                    if node_name == "__interrupt__":
                        continue

                    # Handle intent_planner node output (clarification)
                    if node_name == "retrieval":
                        reasoning_step = allocate_reasoning_step()
                        api_count = len(node_output.get("retrieved_apis", []) or [])
                        table_count = len(node_output.get("retrieved_tables", []) or [])
                        thought = (
                            f"我先检索当前可用的数据源，已找到 {api_count} 个 API"
                            f" 和 {table_count} 张数据库表，接下来开始规划执行路径。"
                        )
                        yield _emit_thought(reasoning_step, thought)
                    elif node_name == "intent_planner":
                        plan = node_output.get("plan", []) or []
                        planning_reasoning = node_output.get("planning_reasoning", "") or ""
                        extracted_filters = node_output.get("extracted_filters", {}) or {}
                        reasoning_step = allocate_reasoning_step()
                        yield _emit_thought(
                            reasoning_step,
                            _build_plan_thought(plan, planning_reasoning, extracted_filters)
                        )

                        plan_by_step_id = {}
                        for index, step in enumerate(plan):
                            step_id = step.get("step_id", index)
                            plan_by_step_id[step_id] = (index, step)

                        messages = node_output.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            if last_msg.get("type") == "clarification":
                                final_answer_text = last_msg.get("content", "")
                                is_clarification = True
                                async for payload in _stream_text(final_answer_text):
                                    yield payload
                    elif node_name == "executor":
                        data_context = node_output.get("data_context", {}) or {}
                        current_plan = node_output.get("plan", []) or []
                        completed_step_ids = node_output.get("completed_step_ids", []) or []

                        if current_plan and not plan_by_step_id:
                            for index, step in enumerate(current_plan):
                                step_id = step.get("step_id", index)
                                plan_by_step_id[step_id] = (index, step)

                        for step_id in completed_step_ids:
                            if step_id in seen_completed_step_ids:
                                continue

                            seen_completed_step_ids.add(step_id)
                            step_index, step = plan_by_step_id.get(step_id, (0, {}))
                            step_number = execution_step_numbers.get(step_id)
                            if step_number is None:
                                step_number = allocate_reasoning_step()
                                execution_step_numbers[step_id] = step_number

                            context_key = (
                                f"step_{step_index}_"
                                f"{step.get('api_id') or step.get('tool', 'unknown')}"
                            )
                            execution_result = data_context.get(context_key)
                            thought = step.get("description") or f"开始执行步骤 {step_id}"

                            yield _emit_thought(step_number, thought)
                            yield _sse("action", {
                                "step": step_number,
                                "action": _build_action_payload(step),
                            })
                            yield _sse("executing", {
                                "step": step_number,
                                "tool": step.get("tool", "unknown"),
                            })
                            yield _sse("observation", {
                                "step": step_number,
                                "content": _summarize_execution_result(execution_result),
                            })

            # Get state after graph paused at analyzer
            state = await graph.aget_state(config)
            if not state.values:
                logger.warning("[StreamChat] Graph state is empty after execution")
            else:
                data_context = state.values.get("data_context", {})
                plan = state.values.get("plan", [])
                error = state.values.get("error")

                # Check if analyzer has data to process (non-error case)
                has_analysis_data = bool(data_context and not error)

                if has_analysis_data:
                    analyzer_step = allocate_reasoning_step()
                    yield _emit_thought(
                        analyzer_step,
                        "数据已经准备好了，我正在整理结果并生成最终回复。"
                    )

                    # F-10: Build state for run_analyzer_stream
                    stream_state: AgentState = {
                        "messages": state.values.get("messages", []),
                        "query": state.values.get("query", user_message),
                        "extracted_filters": state.values.get("extracted_filters"),
                        "plan": plan,
                        "planning_reasoning": state.values.get("planning_reasoning"),
                        "current_step": state.values.get("current_step", 0),
                        "data_context": data_context,
                        "requires_approval": state.values.get("requires_approval", False),
                        "completed_step_ids": state.values.get("completed_step_ids", []),
                    }

                    # Check for simple query (F-01) - skip LLM, use template
                    from app.agent.nodes.analyzer_node import is_simple_query as _is_simple_query, _format_simple_response as _format_simple_response
                    from app.agent.nodes.analyzer_node import _extract_all_data as _extract_all_data_func
                    all_data = _extract_all_data_func(data_context)

                    if _is_simple_query(plan, all_data):
                        logger.info("[StreamChat] Simple query via F-01, using template (no LLM)")
                        final_answer_text = _format_simple_response(all_data, user_message)
                        async for payload in _stream_text(final_answer_text):
                            yield payload
                    else:
                        # F-10: Stream analysis output chunk by chunk
                        logger.info("[StreamChat] Streaming analysis output via SSE")
                        streamed_text = ""
                        async for chunk in run_analyzer_stream(stream_state):
                            streamed_text += chunk
                            yield _sse("streaming_text", {"content": chunk})
                        final_answer_text = streamed_text

                    # Send normalized data
                    for key, value in data_context.items():
                        if isinstance(value, dict) and "data" in value:
                            raw_data = value.get("data")
                            if isinstance(raw_data, dict) and "rows" in raw_data:
                                rows = raw_data.get("rows", [])
                                columns = list(rows[0].keys()) if rows and isinstance(rows[0], dict) else []
                                normalized_data = {"rows": rows, "total": len(rows), "columns": columns}
                            elif isinstance(raw_data, list):
                                if raw_data and isinstance(raw_data[0], dict):
                                    columns = list(raw_data[0].keys())
                                    normalized_data = {"rows": raw_data, "total": len(raw_data), "columns": columns}
                                else:
                                    normalized_data = {"rows": raw_data, "total": len(raw_data), "columns": []}
                            elif isinstance(raw_data, dict):
                                columns = list(raw_data.keys())
                                normalized_data = {"rows": [raw_data], "total": 1, "columns": columns}
                            else:
                                normalized_data = {"rows": [], "total": 0, "columns": []}
                            final_data = normalized_data
                            yield _sse("data", normalized_data)
                            break
                else:
                    # No data or error - emit error/empty response via analyzer fallback
                    analyzer_step = allocate_reasoning_step()
                    yield _emit_thought(
                        analyzer_step,
                        "当前没有拿到可直接分析的数据，我改用解释型回复整理现有结果。"
                    )
                    async for event in graph.astream(None, config, stream_mode="updates"):
                        for node_name, node_output in event.items():
                            if node_name == "analyzer":
                                messages = node_output.get("messages", [])
                                if messages:
                                    final_answer_text = messages[-1].get("content", "")
                                    async for payload in _stream_text(final_answer_text):
                                        yield payload

            # Check if workflow is interrupted (waiting for approval) - skip if we interrupted before analyzer ourselves
            state = await graph.aget_state(config)
            next_nodes = list(state.next) if state.next else []

            if len(next_nodes) == 1 and next_nodes[0] == "analyzer":
                # This is our own interrupt_before, not an approval requirement
                pass
            elif state.next:
                # Workflow is interrupted, send approval_required event
                yield _sse("approval_required", {
                        "thread_id": session_id,
                        "plan": state.values.get("plan", []),
                        "current_step": state.values.get("current_step", 0)
                    })
                yield _sse("done")
                return

            # Save to session storage (for backward compatibility)
            # CRITICAL: Must happen BEFORE done event yield
            if session_id:
                if session_id not in _sessions:
                    _sessions[session_id] = {
                        "messages": [],
                        "created_at": datetime.now(),
                    }
                logger.info(f"[StreamChat] Saving session {session_id}: {len(_sessions[session_id]['messages'])} -> {len(_sessions[session_id]['messages']) + 2} messages")
                _sessions[session_id]["messages"].append({
                    "role": "user",
                    "content": request.message,
                    "timestamp": datetime.now().isoformat(),
                })
                assistant_msg = {
                    "role": "assistant",
                    "content": final_answer_text,
                    "timestamp": datetime.now().isoformat(),
                }
                # F-23: Store thought events in _sessions for history display
                if thought_events:
                    assistant_msg["thought"] = thought_events
                if is_clarification:
                    assistant_msg["type"] = "clarification"
                _sessions[session_id]["messages"].append(assistant_msg)
                _sessions[session_id]["updated_at"] = datetime.now()
                logger.info(f"[StreamChat] Session {session_id} saved with {len(_sessions[session_id]['messages'])} messages")
                _save_sessions()

            # Send done event
            yield _sse("done")

            # Deduct credits (estimate tokens if not provided)
            # For now, use a simple estimation based on response length
            # In production, get actual token count from LLM response
            if total_tokens == 0:
                # Estimate: ~4 chars per token for Chinese
                estimated_input = len(request.message) // 4
                estimated_output = len(final_answer_text) // 4
                total_tokens = estimated_input + estimated_output

            # Get the login_id for credit deduction
            login_id = user_service.get_login_id_by_user_id(user.user_id)

            if login_id:
                deduct_result = credit_service.deduct_credits(
                    login_id=login_id,
                    input_tokens=total_tokens // 2,  # Estimate split
                    output_tokens=total_tokens // 2,
                    query=request.message,
                    session_id=session_id
                )

                # Send quota update event
                quota_event = _json_dumps({
                    "type": "quota",
                    "data": {
                        "credits_deducted": deduct_result.get("credits_deducted", 0),
                        "balance_after": deduct_result.get("balance_after", 0),
                        "is_unlimited": deduct_result.get("is_unlimited", False)
                    }
                }, ensure_ascii=False)
                yield f"data: {quota_event}\n\n"

            # Save to conversation service (backend persistence)
            conversation_service.save_message(
                user_id=user.user_id,
                session_id=session_id,
                role="user",
                content=request.message
            )
            conversation_service.save_message(
                user_id=user.user_id,
                session_id=session_id,
                role="assistant",
                content=final_answer_text,
                data=final_data,
                thought=thought_events  # F-23: Persist thought events for history display
            )

        except Exception as e:
            logger.error(f"Stream chat error: {str(e)}")
            yield _sse("error", {"message": str(e)})

    # F-20: Heartbeat generator — yields SSE comment every 15s to prevent idle timeout
    async def _heartbeat_gen() -> AsyncIterator[str]:
        """SSE heartbeat: ': heartbeat\\n\\n' every 15 seconds to keep connection alive."""
        while True:
            await asyncio.sleep(15)
            yield ": heartbeat\n\n"

    # F-20: Merge event_generator with heartbeat using asyncio.Queue
    async def _merged_generator() -> AsyncIterator[str]:
        """Merges event_generator + heartbeat_generator, yielding items in arrival order."""
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def _enqueue_events():
            """Enqueue all items from event_generator into the shared queue."""
            try:
                async for item in event_generator():
                    await queue.put(item)
            except Exception as e:
                logger.error(f"Enqueue events error: {e}")
            finally:
                await queue.put(None)  # Signal end of main stream

        async def _enqueue_heartbeats():
            """Enqueue heartbeat comments into the shared queue."""
            try:
                async for item in _heartbeat_gen():
                    await queue.put(item)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Enqueue heartbeats error: {e}")

        events_task = asyncio.create_task(_enqueue_events())
        heartbeats_task = asyncio.create_task(_enqueue_heartbeats())
        pending = {events_task, heartbeats_task}

        while pending:
            done, pending = await asyncio.wait(
                pending,
                timeout=15,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Process all available queue items
            while not queue.empty():
                item = queue.get_nowait()
                if item is None:
                    # Main stream ended; cancel heartbeat and drain remaining
                    for t in pending:
                        t.cancel()
                    pending = set()  # Exit loop
                    break
                yield item

        # Drain any remaining items in the queue
        while True:
            try:
                item = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            if item is None:
                break
            yield item

    return StreamingResponse(
        _merged_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
