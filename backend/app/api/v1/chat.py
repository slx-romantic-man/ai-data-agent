"""
Chat API endpoints.
"""
from typing import Dict, Any
import json
import os
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
    """
    suggestion_service = get_suggestion_service()
    suggestions = suggestion_service.get_suggestions(user.user_id)
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

        # Use LangGraph workflow
        graph = await create_graph(permission)

        initial_state: AgentState = {
            "messages": [],
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

        # Update session
        session["messages"].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat(),
        })
        session["messages"].append({
            "role": "assistant",
            "content": final_answer_text,
            "timestamp": datetime.now().isoformat(),
        })
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
        try:
            # Get services
            user_service = get_user_service()
            credit_service = get_credit_service()
            conversation_service = get_conversation_service()

            # Get user account for credit check
            user_account = user_service.get_user_by_user_id(user.user_id)
            if not user_account:
                error_event = _json_dumps({
                    "type": "error",
                    "data": {"message": "用户不存在"}
                }, ensure_ascii=False)
                yield f"data: {error_event}\n\n"
                return

            # Check quota (skip for admin)
            if not user_account.has_unlimited_credits():
                user_service.check_and_reset_if_needed(user.user_id)
                if user_account.quota.current_balance <= 0:
                    error_event = _json_dumps({
                        "type": "error",
                        "data": {
                            "message": "积分不足，请等待每日重置或联系管理员充值",
                            "quota": {
                                "current_balance": user_account.quota.current_balance,
                                "daily_limit": user_account.quota.daily_limit
                            }
                        }
                    }, ensure_ascii=False)
                    yield f"data: {error_event}\n\n"
                    return

            # Get or create session
            session_id = request.session_id or generate_session_id()
            conversation_history = []
            if session_id and session_id in _sessions:
                conversation_history = _sessions[session_id].get(
                    "messages", []
                )

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

            # Create LangGraph workflow
            graph = await create_graph(permission)

            # Initialize state
            initial_state: AgentState = {
                "messages": conversation_history,
                "query": user_message,
                "extracted_filters": None,
                "plan": None,
                "current_step": 0,
                "data_context": {}
            }

            # Stream events from LangGraph
            config = {"configurable": {"thread_id": session_id}}

            async for event in graph.astream(initial_state, config, stream_mode="updates"):
                for node_name, node_output in event.items():
                    # Emit node execution event
                    yield f"data: {_json_dumps({'type': 'thought', 'data': {'content': f'[{node_name}] 节点执行中...'}}, ensure_ascii=False)}\n\n"

                    # Handle intent node output
                    if node_name == "intent":
                        messages = node_output.get("messages", [])
                        if messages:
                            last_msg = messages[-1]
                            if last_msg.get("type") == "clarification":
                                final_answer_text = last_msg.get("content", "")
                                yield f"data: {_json_dumps({'type': 'answer', 'data': {'content': final_answer_text}}, ensure_ascii=False)}\n\n"

                    # Check if this is the final analyzer output
                    if node_name == "analyzer":
                        messages = node_output.get("messages", [])
                        if messages:
                            final_answer_text = messages[-1].get("content", "")
                            yield f"data: {_json_dumps({'type': 'answer', 'data': {'content': final_answer_text}}, ensure_ascii=False)}\n\n"

                        # Send normalized data immediately after analyzer output
                        # Get the current state from the graph to access data_context
                        current_state = await graph.aget_state(config)

                        if current_state.values:
                            data_context = current_state.values.get("data_context", {})
                            logger.info(f"[SSE] data_context from state: {len(data_context)} keys, keys={list(data_context.keys())}")

                            if data_context:
                                for key, value in data_context.items():
                                    if isinstance(value, dict) and "data" in value:
                                        # Normalize data to {rows: [...], row_count: N} format
                                        raw_data = value.get("data")
                                        logger.info(f"[SSE] Normalizing data for key={key}, raw_data_type={type(raw_data).__name__}")

                                        # Case 1: Already has 'rows' field
                                        if isinstance(raw_data, dict) and "rows" in raw_data:
                                            normalized_data = {
                                                "rows": raw_data.get("rows", []),
                                                "row_count": len(raw_data.get("rows", []))
                                            }
                                            logger.info(f"[SSE] Case 1: Already has rows field, row_count={normalized_data['row_count']}")

                                        # Case 2: List format
                                        elif isinstance(raw_data, list):
                                            normalized_data = {
                                                "rows": raw_data,
                                                "row_count": len(raw_data)
                                            }
                                            logger.info(f"[SSE] Case 2: List format, row_count={normalized_data['row_count']}")

                                        # Case 3: Single dict format (e.g., weather/IP API response)
                                        elif isinstance(raw_data, dict):
                                            normalized_data = {
                                                "rows": [raw_data],
                                                "row_count": 1
                                            }
                                            logger.info(f"[SSE] Case 3: Single dict format (weather/IP API), row_count=1")

                                        # Case 4: No data or invalid format
                                        else:
                                            normalized_data = {
                                                "rows": [],
                                                "row_count": 0
                                            }
                                            logger.warning(f"[SSE] Case 4: Invalid format or no data")

                                        yield f"data: {_json_dumps({'type': 'data', 'data': normalized_data}, ensure_ascii=False)}\n\n"
                                        logger.info(f"[SSE] Sent normalized data event with rows field")
                                        break

            # Check if workflow is interrupted (waiting for approval)
            state = await graph.aget_state(config)

            if state.next:
                # Workflow is interrupted, send approval_required event
                approval_event = _json_dumps({
                    "type": "approval_required",
                    "data": {
                        "thread_id": session_id,
                        "plan": state.values.get("plan", []),
                        "current_step": state.values.get("current_step", 0)
                    }
                }, ensure_ascii=False)
                yield f"data: {approval_event}\n\n"
                yield f"data: {_json_dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                return

            # Send done event
            yield f"data: {_json_dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

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
                data=final_data
            )

            # Also save to session storage (for backward compatibility)
            if session_id:
                if session_id not in _sessions:
                    _sessions[session_id] = {
                        "messages": [],
                        "created_at": datetime.now(),
                    }
                _sessions[session_id]["messages"].append({
                    "role": "user",
                    "content": request.message,
                    "timestamp": datetime.now().isoformat(),
                })
                _sessions[session_id]["messages"].append({
                    "role": "assistant",
                    "content": final_answer_text,
                    "timestamp": datetime.now().isoformat(),
                })
                _sessions[session_id]["updated_at"] = datetime.now()
                _save_sessions()

        except Exception as e:
            logger.error(f"Stream chat error: {str(e)}")
            error_event = _json_dumps({
                "type": "error",
                "data": {"message": str(e)}
            }, ensure_ascii=False)
            yield f"data: {error_event}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )