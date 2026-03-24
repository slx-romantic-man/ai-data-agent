"""
Streaming ReAct Agent Engine.
"""
import asyncio
import json
import re
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, List, AsyncGenerator

from app.config.llm_config import BaseLLMClient, get_llm
from app.config.settings import settings
from app.models.user import UserContext
from app.models.chat import ReasoningLog, ReasoningStep
from app.models.permission import PermissionContext
from app.agent.prompts.react_prompt import (
    get_react_system_prompt,
)
from app.agent.router.tool_router import ToolRouter, get_tool_router
from app.agent.core.circuit_breaker import get_react_circuit_breaker
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StreamingReActAgent:
    """Streaming ReAct Agent with real-time output."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self._llm = llm_client
        self._tool_router: Optional[ToolRouter] = None
        self._initialized = False
        self._total_tokens = 0  # Token counter for circuit breaker
        self._circuit_breaker = get_react_circuit_breaker()
        self._api_retrieval_service = None  # API retrieval service for two-stage selection
        self._permission_service = None
        self._allowed_api_identifiers = set()
        self._allowed_api_endpoints: Dict[str, set[str]] = {}
        self._relevant_api_identifiers = set()
        self._relevant_api_endpoints: Dict[str, set[str]] = {}

    async def initialize(self):
        if self._initialized:
            return
        self._tool_router = await get_tool_router()
        self._initialized = True

    @property
    def tool_router(self) -> ToolRouter:
        if self._tool_router is None:
            raise RuntimeError("ToolRouter not initialized.")
        return self._tool_router

    @property
    def llm(self) -> BaseLLMClient:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    async def _get_api_retrieval_service(self):
        """Lazy load API retrieval service."""
        if self._api_retrieval_service is None:
            from app.services.api_retrieval_service import get_api_retrieval_service
            self._api_retrieval_service = get_api_retrieval_service()
        return self._api_retrieval_service

    async def _get_permission_service(self):
        """Lazy load API permission service."""
        if self._permission_service is None:
            from app.services.api_permission_service import get_api_permission_service
            self._permission_service = await get_api_permission_service()
        return self._permission_service

    def _format_relevant_apis(self, apis: List[Dict[str, Any]]) -> str:
        """
        Format relevant APIs for injection into system prompt.

        Args:
            apis: List of API dicts with id, name, description, endpoints

        Returns:
            Formatted string for prompt injection
        """
        if not apis:
            return "暂无可用的相关API"

        formatted = []
        for i, api in enumerate(apis, 1):
            api_id = api.get("config_id") or api.get("id", "unknown")
            name = api.get("name", "未知API")
            description = api.get("description", "")
            endpoints = api.get("endpoints", [])

            endpoints_str = ""
            if endpoints:
                endpoint_list = []
                for ep in endpoints:
                    if isinstance(ep, dict):
                        ep_name = ep.get("name", ep.get("endpoint", "unknown"))
                        ep_desc = ep.get("description", "")
                        endpoint_list.append(f"{ep_name}({ep_desc})")
                    else:
                        endpoint_list.append(str(ep))
                endpoints_str = ", ".join(endpoint_list)

            formatted.append(
                f"{i}. [{api_id}] {name}\n"
                f"   描述: {description}\n"
                f"   端点: {endpoints_str}"
            )

        return "\n".join(formatted)

    def _extract_api_identifiers(self, api: Dict[str, Any]) -> set[str]:
        """Extract all valid identifiers for one API."""
        identifiers = set()
        for key in ("config_id", "id", "api_id"):
            value = api.get(key)
            if value is not None and value != "":
                identifiers.add(str(value))
        return identifiers

    def _extract_api_endpoints(self, api: Dict[str, Any]) -> set[str]:
        """Extract endpoint names for one API."""
        endpoints = api.get("endpoints") or {}
        endpoint_names: set[str] = set()

        if isinstance(endpoints, dict):
            for name in endpoints.keys():
                endpoint_names.add(str(name))
            return endpoint_names

        if isinstance(endpoints, list):
            for endpoint in endpoints:
                if isinstance(endpoint, dict):
                    name = endpoint.get("name") or endpoint.get("endpoint")
                    if name:
                        endpoint_names.add(str(name))
                elif endpoint:
                    endpoint_names.add(str(endpoint))

        return endpoint_names

    def _register_api_constraints(
        self,
        apis: List[Dict[str, Any]],
        target_identifiers: set[str],
        target_endpoints: Dict[str, set[str]],
    ) -> None:
        """Populate API identifier and endpoint constraints."""
        target_identifiers.clear()
        target_endpoints.clear()

        for api in apis:
            identifiers = self._extract_api_identifiers(api)
            endpoints = self._extract_api_endpoints(api)
            target_identifiers.update(identifiers)

            for identifier in identifiers:
                target_endpoints[identifier] = set(endpoints)

    def _resolve_default_api_and_endpoint(
        self,
        api_id: str,
        endpoint: str,
    ) -> tuple[str, str]:
        """Resolve missing api_id/endpoint from constrained candidates."""
        resolved_api_id = str(api_id) if api_id else ""
        resolved_endpoint = str(endpoint) if endpoint else ""

        if not resolved_api_id:
            if len(self._relevant_api_identifiers) == 1:
                resolved_api_id = next(iter(self._relevant_api_identifiers))
            elif len(self._allowed_api_identifiers) == 1:
                resolved_api_id = next(iter(self._allowed_api_identifiers))

        if resolved_api_id and not resolved_endpoint:
            relevant_endpoints = self._relevant_api_endpoints.get(resolved_api_id)
            allowed_endpoints = self._allowed_api_endpoints.get(resolved_api_id)
            endpoint_pool = relevant_endpoints or allowed_endpoints or set()
            if len(endpoint_pool) == 1:
                resolved_endpoint = next(iter(endpoint_pool))

        return resolved_api_id, resolved_endpoint

    def _is_api_allowed(self, api_id: str) -> bool:
        """Validate API identifier against permission-constrained set."""
        return str(api_id) in self._allowed_api_identifiers

    def _is_endpoint_allowed(self, api_id: str, endpoint: str) -> bool:
        """Validate endpoint name for a given API."""
        api_key = str(api_id)
        endpoint_key = str(endpoint)

        relevant_endpoints = self._relevant_api_endpoints.get(api_key)
        if relevant_endpoints:
            return endpoint_key in relevant_endpoints

        allowed_endpoints = self._allowed_api_endpoints.get(api_key)
        if allowed_endpoints:
            return endpoint_key in allowed_endpoints

        return False

    def _top_allowed_api_ids_text(self, limit: int = 8) -> str:
        """Format allowed API ids for model feedback."""
        if not self._allowed_api_identifiers:
            return "[]"

        sorted_ids = sorted(self._allowed_api_identifiers)
        return ", ".join(sorted_ids[:limit])

    def _allowed_endpoints_text(self, api_id: str) -> str:
        """Format allowed endpoint list for one API."""
        endpoints = self._allowed_api_endpoints.get(str(api_id), set())
        if not endpoints:
            return "[]"
        return ", ".join(sorted(endpoints))

    async def _get_relevant_apis(
        self,
        user_query: str,
        user_id: str,
    ) -> str:
        """Get relevant APIs using two-stage retrieval (vector + LLM)."""
        logger.info(f"[_get_relevant_apis] Called with query='{user_query}', user_id='{user_id}'")
        allowed_apis: List[Dict[str, Any]] = []

        try:
            logger.info("[_get_relevant_apis] Getting permission service...")
            permission_service = await self._get_permission_service()
            logger.info("[_get_relevant_apis] Getting active API IDs...")
            active_ids = await permission_service.get_active_api_ids(user_id)
            logger.info(f"[_get_relevant_apis] Found {len(active_ids)} active API IDs")
            for api_config_id in active_ids:
                api = await permission_service.get_api_with_auth(api_config_id)
                if api:
                    allowed_apis.append(api)
        except Exception as db_error:
            logger.error(f"Failed to load allowed APIs: {db_error}")

        self._register_api_constraints(
            allowed_apis,
            self._allowed_api_identifiers,
            self._allowed_api_endpoints,
        )

        if not allowed_apis:
            self._relevant_api_identifiers.clear()
            self._relevant_api_endpoints.clear()
            return "暂无可用的相关API"

        # Use two-stage retrieval service for large-scale API selection
        logger.info(f"Starting API retrieval for query: {user_query}")
        if True:
            try:
                logger.info("Getting retrieval service...")
                retrieval_service = await self._get_api_retrieval_service()
                logger.info(f"Calling get_apis_for_query with user_id={user_id}")
                relevant_apis = await retrieval_service.get_apis_for_query(
                    query=user_query,
                    user_id=user_id,
                    top_k=None,  # Use settings.API_RETRIEVAL_FINAL_TOP_K
                )
                logger.info(f"Retrieval returned {len(relevant_apis) if relevant_apis else 0} APIs")
                if relevant_apis:
                    logger.info(f"Retrieved {len(relevant_apis)} relevant APIs for query: {user_query}")
                    self._register_api_constraints(
                        relevant_apis,
                        self._relevant_api_identifiers,
                        self._relevant_api_endpoints,
                    )
                    return self._format_relevant_apis(relevant_apis)
                else:
                    logger.warning("Retrieval returned empty list, falling back")
            except Exception as retrieval_error:
                import traceback
                logger.error(f"Failed to get relevant APIs: {retrieval_error}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                logger.warning(f"Falling back to all allowed APIs")

        # Fallback: use all allowed APIs (limited to top 8)
        self._register_api_constraints(
            allowed_apis,
            self._relevant_api_identifiers,
            self._relevant_api_endpoints,
        )

        return self._format_relevant_apis(allowed_apis[:8])

    async def process_stream(
        self,
        user_query: str,
        user_context: UserContext,
        conversation_history: List[Dict[str, str]] = None,
        permission_context: PermissionContext = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process query with streaming output.

        Args:
            user_query: The user's question
            user_context: User context with role, department, etc.
            conversation_history: Previous conversation messages
            permission_context: Pre-built permission context (from API layer)
        """
        # Permission context must be provided by API layer
        if permission_context is None:
            raise TypeError(
                "permission_context must be provided by API layer. "
                "Use get_permission_context dependency in your API endpoint."
            )

        reasoning_log = ReasoningLog()
        all_data = []
        final_sql = ""
        self._total_tokens = 0  # Reset token counter

        yield {"type": "start", "data": {"query": user_query}}

        # Circuit breaker: Check if requests are allowed
        if not self._circuit_breaker.can_execute():
            stats = self._circuit_breaker.stats
            yield self._format_error(
                f"服务暂时不可用，请稍后重试。"
                f"(连续失败: {stats.consecutive_failures}次，"
                f"请等待约{int(self._circuit_breaker.recovery_timeout)}秒后重试)"
            )
            return

        try:
            async with asyncio.timeout(settings.REACT_LOOP_TIMEOUT_SECONDS):
                iteration = 1
                is_finished = False
                # Get relevant APIs using two-stage retrieval
                relevant_apis = await self._get_relevant_apis(
                    user_query, user_context.user_id
                )

                while iteration <= settings.REACT_MAX_ITERATIONS and not is_finished:
                    # Circuit breaker: Check token budget
                    if self._total_tokens >= settings.REACT_MAX_TOKENS_PER_QUERY:
                        yield self._format_error(
                            f"查询消耗的 token 已超出预算 "
                            f"({settings.REACT_MAX_TOKENS_PER_QUERY})，请简化问题。"
                        )
                        break

                    # Build context for this iteration
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    system_prompt = get_react_system_prompt(
                        tool_descriptions=self._build_tool_descriptions(),
                        user_role=user_context.role or "user",
                        data_scope=user_context.department or "all",
                        relevant_apis=relevant_apis,
                        current_date=current_date
                    )

                    # Get current messages including tool results
                    current_messages = [
                        {"role": "system", "content": system_prompt}
                    ] + (conversation_history or []) + reasoning_log.to_messages()

                    # Add the user's initial query or a prompt to continue
                    if iteration == 1:
                        current_messages.append({
                            "role": "user",
                            "content": user_query
                        })
                    else:
                        current_messages.append({
                            "role": "user",
                            "content": "请继续思考并选择一个工具执行。"
                        })

                    try:
                        # Request LLM for thought + action with streaming
                        full_response = ""
                        current_thought = ""

                        async for chunk in self.llm.chat_stream(current_messages):
                            full_response += chunk

                            # Detect Thought in streaming
                            thought_match = re.search(
                                r'Thought:\s*(.*?)(?=\s*\n\s*(Action|Answer)|$)',
                                full_response,
                                re.DOTALL | re.IGNORECASE
                            )

                            if thought_match:
                                thought_content = thought_match.group(1).strip()
                                if thought_content and thought_content != current_thought:
                                    yield {
                                        "type": "thought",
                                        "data": {
                                            "step": iteration,
                                            "content": thought_content
                                        }
                                    }
                                    current_thought = thought_content
                            elif full_response.strip() and len(full_response.strip()) > 2:
                                display_content = full_response.strip()
                                if display_content != current_thought:
                                    yield {
                                        "type": "thought",
                                        "data": {
                                            "step": iteration,
                                            "content": display_content
                                        }
                                    }
                                    current_thought = display_content

                        response = full_response
                        logger.info(
                            f"Iteration {iteration} LLM full response received."
                        )
                        logger.info(f"[DEBUG] LLM Response: {response[:500]}")
                    except Exception as e:
                        yield self._error_event(f"LLM error: {str(e)}")
                        return

                    # Parse: Final parse for structural components
                    thought, action, answer = self._parse_response(response)
                    logger.info(f"[DEBUG] LLM Response (first 1000 chars): {response[:1000]}")
                    logger.info(
                        f"Final Parse - thought: "
                        f"{(thought[:50] if thought else 'None')}..., "
                        f"action: {action}, answer: {(answer[:50] if answer else 'None')}"
                    )

                    step = ReasoningStep(step_number=iteration, thought=thought)

                    # Push thought if exists
                    if thought:
                        yield {
                            "type": "thought",
                            "data": {"step": iteration, "content": thought}
                        }

                    if answer:
                        is_finished = True
                        reasoning_log.final_answer = answer
                        reasoning_log.is_complete = True
                        step.observation = "任务完成"
                        reasoning_log.add_step(step)
                        yield {
                            "type": "answer",
                            "data": {
                                "content": answer,
                                "reasoning_log": self._to_dict(reasoning_log)
                            }
                        }
                        if all_data:
                            yield {
                                "type": "data",
                                "data": {
                                    "columns": (
                                        list(all_data[0].keys())
                                        if all_data else []
                                    ),
                                    "rows": all_data,
                                    "total": len(all_data),
                                    "sql": final_sql
                                }
                            }
                        break

                    if action:
                        step.action = action
                        yield {
                            "type": "action",
                            "data": {"step": iteration, "action": action}
                        }

                        yield {
                            "type": "executing",
                            "data": {
                                "step": iteration,
                                "tool": action.get("tool", "unknown")
                            }
                        }

                        observation, res_data, sql = await self._execute_action(
                            action,
                            permission_context,
                        )
                        step.observation = observation
                        if res_data:
                            all_data = res_data
                        if sql:
                            final_sql = sql

                        yield {
                            "type": "observation",
                            "data": {"step": iteration, "content": observation}
                        }
                    else:
                        # Fallback logic: If no direct ACTION or ANSWER found
                        remaining_content = self._get_non_thought_content(response)
                        if remaining_content and len(remaining_content) > 10:
                            is_finished = True

                            if thought:
                                yield {
                                    "type": "thought",
                                    "data": {
                                        "step": iteration,
                                        "content": thought
                                    }
                                }

                            reasoning_log.final_answer = remaining_content
                            reasoning_log.is_complete = True
                            step.observation = "解析到隐式回答"
                            reasoning_log.add_step(step)
                            yield {
                                "type": "answer",
                                "data": {
                                    "content": remaining_content,
                                    "reasoning_log": self._to_dict(reasoning_log)
                                }
                            }
                            if all_data:
                                yield {
                                    "type": "data",
                                    "data": {
                                        "columns": (
                                            list(all_data[0].keys())
                                            if all_data else []
                                        ),
                                        "rows": all_data,
                                        "total": len(all_data),
                                        "sql": final_sql
                                    }
                                }
                            break
                        else:
                            is_finished = True
                            step.observation = "未检测到有效动作或回答"

                    reasoning_log.add_step(step)
                    iteration += 1

                # Final check - if we exited loop and still haven't sent answer
                if not is_finished:
                    for idx, step in enumerate(reasoning_log.steps, 1):
                        if step.thought:
                            yield {
                                "type": "thought",
                                "data": {"step": idx, "content": step.thought}
                            }

                    final_text = await self._generate_final_response(
                        user_query, reasoning_log
                    )
                    yield {
                        "type": "answer",
                        "data": {
                            "content": final_text,
                            "reasoning_log": self._to_dict(reasoning_log)
                        }
                    }

                if all_data:
                    yield {
                        "type": "data",
                        "data": {
                            "columns": list(all_data[0].keys()) if all_data else [],
                            "rows": all_data,
                            "total": len(all_data),
                            "sql": final_sql
                        }
                    }

                yield {
                    "type": "done",
                    "data": {"reasoning_log": self._to_dict(reasoning_log)}
                }

                # Circuit breaker: Record success
                self._circuit_breaker.record_success()

        except asyncio.TimeoutError:
            self._circuit_breaker.record_failure()
            yield self._format_error("查询超时，请简化问题或稍后重试。")
        except Exception as e:
            self._circuit_breaker.record_failure(e)
            logger.error(f"Stream error: {traceback.format_exc()}")
            yield self._error_event(str(e))

    def _error_event(self, message: str) -> Dict:
        return {"type": "error", "data": {"message": message}}

    def _format_error(self, message: str) -> Dict:
        """Format an error message for circuit breaker."""
        return {"type": "error", "data": {"message": message}}

    def _to_dict(self, model: Any) -> Dict[str, Any]:
        """Convert a pydantic model or dict to a dictionary for SSE."""
        if hasattr(model, "dict"):
            data = model.dict()
        elif hasattr(model, "model_dump"):
            data = model.model_dump()
        elif isinstance(model, dict):
            data = model
        else:
            return str(model)
            
        # Convert datetime fields to ISO strings if it's a reasoning log
        if isinstance(data, dict) and "steps" in data:
            for step in data.get("steps", []):
                if step.get("timestamp"):
                    ts = step["timestamp"]
                    step["timestamp"] = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
        return data

    def _parse_response(self, response: str) -> tuple:
        """Parse LLM response for Thought, Action, and Answer."""
        thought = None
        action = None
        answer = None

        # Extract Thought
        m = re.search(
            r'Thought:\s*(.+?)(?=\n\s*(?:Action|Answer):|$)',
            response, re.DOTALL | re.IGNORECASE
        )
        if m:
            thought = m.group(1).strip()
        else:
            # If no Action/Answer follows, capture everything after Thought:
            m = re.search(r'Thought:\s*(.+)', response, re.DOTALL | re.IGNORECASE)
            if m:
                thought = m.group(1).strip()

        # Check if this is a clarification question (missing info)
        # Pattern: Thought contains question asking for specific info, no Action
        if thought and not re.search(r'Action:', response, re.IGNORECASE):
            # Check if thought contains question patterns
            question_patterns = [
                r'请提供.*?[？?]',
                r'请.*?指定.*?[？?]',
                r'需要.*?信息',
                r'缺少.*?参数',
                r'请问.*?[？?]',
            ]
            for pattern in question_patterns:
                if re.search(pattern, thought):
                    # This is a clarification question, treat as Answer
                    answer = thought
                    thought = None
                    break

        # Extract Action - 使用更健壮的JSON解析方法
        # 首先尝试 <JSON>...</JSON> 格式
        m = re.search(r'Action:\s*<JSON>(.+?)</JSON>', response, re.DOTALL)
        if m:
            action_str = m.group(1).strip()
        else:
            # 使用更健壮的方法：找到 Action: 后面的完整JSON对象
            action_start = re.search(r'Action:\s*', response, re.IGNORECASE)
            if action_start:
                # 从 Action: 后面开始查找 JSON
                json_start_idx = action_start.end()
                # 找到第一个 { 的位置
                brace_start = response.find('{', json_start_idx)
                if brace_start != -1:
                    # 使用括号匹配来找到完整的JSON
                    brace_count = 0
                    json_end = brace_start
                    for i, char in enumerate(response[brace_start:], brace_start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    action_str = response[brace_start:json_end].strip()
                else:
                    action_str = None
            else:
                action_str = None

        if action_str:
            try:
                action = json.loads(action_str)
            except json.JSONDecodeError:
                # Try to fix: add quotes to unquoted keys
                fixed = re.sub(r'(\{|,)\s*(\w+)\s*:', r'\1"\2":', action_str)
                try:
                    action = json.loads(fixed)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse action: {action_str}")
                    action = None

        # 确保 action 是字典类型
        if action is not None and not isinstance(action, dict):
            logger.error(f"Action is not a dict: {type(action)}, value: {action}")
            action = None

        # Extract Answer
        m = re.search(r'Answer:\s*(.+)', response, re.DOTALL | re.IGNORECASE)
        if m:
            answer = m.group(1).strip()

        return thought, action, answer

    def _get_non_thought_content(self, response: str) -> str:
        """Extract content after Thought that isn't Thought/Action/Answer."""
        # Remove Thought: ... 
        content = re.sub(
            r'Thought:\s*.*?(?=\s*\n\s*(Action|Answer)|$)',
            '',
            response,
            flags=re.DOTALL | re.IGNORECASE
        ).strip()
        # Remove Action: ... and Answer: ... if they exist
        content = re.sub(
            r'(Action|Answer):\s*.*',
            '',
            content,
            flags=re.DOTALL | re.IGNORECASE
        ).strip()
        return content

    async def _execute_action(
        self,
        action: Dict,
        permission: PermissionContext,
    ) -> tuple:
        """Execute action and return (observation, data, sql).

        Args:
            action: The action to execute
            permission: Pre-built permission context (from API layer)
        """
        tool_name = action.get("tool", action.get("name", ""))
        parameters = action.get("parameters", action.get("params", {}))
        if not isinstance(parameters, dict):
            parameters = {}

        # 处理简化格式：如果 action 中没有 "tool" 键，但有 "api_id" 键
        # 说明 LLM 使用了简化格式：api_fetch {"api_id": "geo", ...}
        if not tool_name and "api_id" in action:
            tool_name = "api_fetch"
            parameters = action

        observation = ""
        result_data = []
        sql = ""

        # Permission context must be provided by API layer
        if permission is None:
            raise TypeError(
                "permission context must be provided by API layer. "
                "This is a programming error - check that permission_context "
                "is being passed correctly from process_stream."
            )

        try:
            if not tool_name or tool_name == "api_fetch":
                api_id = (
                    parameters.get("api_id")
                    or parameters.get("api_config_id", "")
                )
                endpoint = parameters.get("endpoint", "")

                actual_params = parameters.get("params", {})
                if not isinstance(actual_params, dict):
                    actual_params = {}

                reserved_keys = {
                    "api_id",
                    "api_config_id",
                    "endpoint",
                    "params",
                    "tool",
                    "parameters",
                }
                for key, value in parameters.items():
                    if key not in reserved_keys:
                        actual_params[key] = value

                api_id, endpoint = self._resolve_default_api_and_endpoint(
                    api_id,
                    endpoint,
                )

                if not api_id:
                    allowed_text = self._top_allowed_api_ids_text()
                    observation = (
                        "缺少合法 api_id。"
                        f"请从当前可用API中选择: {allowed_text}"
                    )
                    return observation, result_data, sql

                if not self._is_api_allowed(api_id):
                    allowed_text = self._top_allowed_api_ids_text()
                    observation = (
                        f"API不在授权范围: {api_id}。"
                        f"请改用可用API: {allowed_text}"
                    )
                    return observation, result_data, sql

                if not endpoint:
                    allowed_eps = self._allowed_endpoints_text(api_id)
                    observation = (
                        f"缺少 endpoint，API {api_id} 可用端点: {allowed_eps}"
                    )
                    return observation, result_data, sql

                if not self._is_endpoint_allowed(api_id, endpoint):
                    allowed_eps = self._allowed_endpoints_text(api_id)
                    observation = (
                        f"端点不在授权范围: {api_id}/{endpoint}。"
                        f"可用端点: {allowed_eps}"
                    )
                    return observation, result_data, sql

                tool = self.tool_router.get_tool("api_fetch")
                if tool:
                    result = await tool.execute(
                        {
                            "api_id": api_id,
                            "endpoint": endpoint,
                            "params": actual_params
                        },
                        permission
                    )
                    status_str = str(getattr(result, "status", "")).replace(
                        "ToolStatus.", ""
                    ).lower()

                    if result and status_str == "success" and getattr(
                        result, "data", None
                    ) is not None:
                        # Clean API data: Extract business data from common response
                        # structures like {"code": 0, "message": "...", "data": [...]}
                        raw_data = result.data
                        cleaned_data = raw_data
                        if isinstance(raw_data, dict):
                            # Try to extract 'data' or 'items' or 'list'
                            for key in ["data", "items", "list", "result"]:
                                if key in raw_data and isinstance(
                                    raw_data[key], (list, dict)
                                ):
                                    cleaned_data = raw_data[key]
                                    break
                        
                        if isinstance(cleaned_data, list):
                            result_data = cleaned_data
                        elif isinstance(cleaned_data, dict):
                            result_data = [cleaned_data]
                        else:
                            result_data = [cleaned_data]

                        # 构建包含统计信息的observation
                        observation = self._build_data_observation(result_data)
                        sql = f"API: {api_id}/{endpoint}"
                    elif result and status_str == "failed":
                        observation = f"API调用失败: {result.error or '未知错误'}"
                    else:
                        observation = "API调用成功，未返回数据"
            elif tool_name == "export_excel":
                # Special handling for export with preview/review
                tool = self.tool_router.get_tool("export_excel")
                if tool:
                    # In this phase, we just execute it, but we prepare for 
                    # the preview log in the next step.
                    result = await tool.execute(parameters, permission)
                    status_str = str(getattr(result, "status", "")).replace(
                        "ToolStatus.", ""
                    ).lower()
                    if result and status_str == "success":
                        file_info = result.data
                        preview = file_info.get("preview", [])
                        observation = (
                            f"导出成功！请检查以下导出数据预览（前5行）：\n"
                            f"路径: {file_info.get('file_path')}\n"
                            f"预览: {json.dumps(preview, ensure_ascii=False)}\n\n"
                            "⚠️ 检查要点：1. 表头是否为纯净业务名？2. 数据是否对齐？\n"
                            "如果样式不佳，请根据预览给出修正参数重新执行导出动作。"
                        )
                    else:
                        observation = f"导出失败: {result.error or '未知错误'}"
            else:
                observation = f"未知工具: {tool_name}"

        except Exception as e:
            observation = f"执行失败: {str(e)}"

        return observation, result_data, sql

    async def _generate_final_response(
        self, user_query: str, reasoning_log: ReasoningLog
    ) -> str:
        if reasoning_log.final_answer:
            return reasoning_log.final_answer

        history = []
        for step in reasoning_log.steps:
            if step.thought:
                history.append(f"思考: {step.thought}")
            if step.observation:
                history.append(f"观察: {step.observation}")

        messages = [
            {
                "role": "system",
                "content": "你是企业数据分析助手，请简洁回答。"
            },
            {
                "role": "user",
                "content": f"问题：{user_query}\n\n推理：{chr(10).join(history)}\n\n回答："
            }
        ]
        return await self.llm.chat(messages)

    def _build_data_observation(self, data: List[Dict[str, Any]]) -> str:
        """
        构建包含统计信息的数据观察结果。
        自动识别日期字段和数值字段，提供关键统计信息。
        """
        if not data:
            return "API调用成功，但未返回数据"

        observation_parts = [f"获取到 {len(data)} 条数据"]

        # 识别日期字段（常见日期字段名）
        date_field_names = ['date', 'order_date', 'created_at', 'updated_at', 'time', 'datetime', 'start_date', 'end_date']

        # 收集所有字段的值
        field_values: Dict[str, List] = {}
        for row in data:
            for key, value in row.items():
                if key not in field_values:
                    field_values[key] = []
                if value is not None:
                    field_values[key].append(value)

        # 分析日期字段
        date_fields_found = []
        for field_name in date_field_names:
            if field_name in field_values and field_values[field_name]:
                values = field_values[field_name]
                # 检查是否为日期格式
                sample = str(values[0])
                if '-' in sample or '/' in sample:  # 简单判断是否为日期格式
                    unique_values = sorted(set(str(v) for v in values))
                    if len(unique_values) > 1:
                        date_range = f"{unique_values[0]} 至 {unique_values[-1]}"
                    else:
                        date_range = unique_values[0]
                    date_fields_found.append(f"{field_name}: {date_range}")

        if date_fields_found:
            observation_parts.append("日期范围: " + ", ".join(date_fields_found))

        # 分析数值字段（取前几个重要数值字段）
        numeric_stats = []
        for key, values in field_values.items():
            if key.lower() in ['id', '_id', 'order_id', 'item_id']:
                continue  # 跳过ID字段
            if values and isinstance(values[0], (int, float)):
                numeric_values = [v for v in values if isinstance(v, (int, float))]
                if numeric_values:
                    total = sum(numeric_values)
                    avg = total / len(numeric_values)
                    min_val = min(numeric_values)
                    max_val = max(numeric_values)
                    numeric_stats.append(
                        f"{key}: 总计{total:.2f}, 均值{avg:.2f}, 范围[{min_val:.2f}-{max_val:.2f}]"
                    )

        if numeric_stats:
            observation_parts.append("数值统计: " + "; ".join(numeric_stats[:3]))  # 最多显示3个数值字段

        # 显示数据样例（限制在3条以内）
        if len(data) > 0:
            sample_count = min(3, len(data))
            sample_str = json.dumps(data[:sample_count], ensure_ascii=False)
            observation_parts.append(f"数据样例: {sample_str}")

        return "。".join(observation_parts)

    def _build_tool_descriptions(self) -> str:
        return (
            "1. api_fetch - 调用API获取数据\n"
            "   格式: {\"tool\": \"api_fetch\", \"parameters\": "
            "{\"api_id\": \"API的ID\", \"endpoint\": \"端点名称\", "
            "\"params\": {...}}}"
        )


# Global instance
_streaming_agent: Optional[StreamingReActAgent] = None


async def get_streaming_agent() -> StreamingReActAgent:
    global _streaming_agent
    if _streaming_agent is None:
        _streaming_agent = StreamingReActAgent()
        await _streaming_agent.initialize()
    return _streaming_agent