"""
API Fetch Tool - 从外部API获取数据
支持通用URL调用和配置化API调用
集成权限管理系统
"""
from typing import Any, Dict, Optional
import aiohttp
import re
import os
import base64
import time

from app.agent.tools.base_tool import BaseTool
from app.models.permission import PermissionContext
from app.models.tool import ToolResult
from app.config.api_config import get_api_registry, AuthType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class APIFetchTool(BaseTool):
    """
    API数据获取工具
    支持两种模式：
    1. 直接URL调用 - 提供完整URL
    2. 配置化API调用 - 使用预配置的API ID和端点名（需权限验证）
    """

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._permission_service = None  # Lazy-loaded permission service

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60.0)
            )
        return self._session

    async def _get_permission_service(self):
        """Lazy load permission service."""
        if self._permission_service is None:
            from app.services.api_permission_service import get_api_permission_service
            self._permission_service = await get_api_permission_service()
        return self._permission_service

    @property
    def name(self) -> str:
        return "api_fetch"

    @property
    def description(self) -> str:
        return """从外部API获取数据。
支持两种方式：
1. 直接URL: {"url": "https://api.example.com/data"}
2. 配置化: {"api_id": "inv", "endpoint": "query", "params": {"id": "123"}}
"""

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                # 方式1: 直接URL
                "url": {"type": "string", "description": "完整的API URL"},
                "method": {"type": "string", "enum": ["GET", "POST"], "default": "GET"},
                "headers": {"type": "object", "description": "请求头"},
                "params": {"type": "object", "description": "查询参数"},
                "body": {"type": "object", "description": "POST请求体"},
                # 方式2: 配置化API
                "api_id": {"type": "string", "description": "预配置的API ID"},
                "endpoint": {"type": "string", "description": "API端点名"},
                "path_params": {"type": "object", "description": "路径参数"},
            },
        }

    async def execute(
        self,
        params: Dict[str, Any],
        permission: PermissionContext,
    ) -> ToolResult:
        """执行API请求"""

        # 判断调用模式
        if "api_id" in params and "endpoint" in params:
            return await self._execute_configured_api(params, permission)
        elif "url" in params:
            return await self._execute_direct_url(params, permission)
        else:
            return self._error("缺少必要参数：需要提供 url 或 (api_id + endpoint)")

    async def _execute_configured_api(
        self,
        params: Dict[str, Any],
        permission: PermissionContext,
    ) -> ToolResult:
        """执行配置化API调用（带权限验证）"""
        api_id = params.get("api_id")
        endpoint_name = params.get("endpoint")
        request_params = params.get("params", {})
        path_params = params.get("path_params", {})

        # ==================== 权限检查 ====================
        # 首先尝试从数据库权限系统获取API配置
        permission_service = await self._get_permission_service()

        # 尝试从数据库获取API配置ID
        # api_id 可能是 config_id (string) 或数字 ID
        db_api_config = None
        api_config_id_int = None

        # 尝试解析为数字ID
        try:
            api_config_id_int = int(api_id)
        except (ValueError, TypeError):
            # 不是数字，可能是 config_id，需要查找对应的数字ID
            from app.access.database.connection import get_db
            from app.access.database.models import APIConfig
            from sqlalchemy import select

            db = await get_db()
            async with db.get_session() as session:
                result = await session.execute(
                    select(APIConfig).where(APIConfig.config_id == api_id)
                )
                api_record = result.scalar_one_or_none()
                if api_record:
                    api_config_id_int = api_record.id

        # 验证用户权限
        if api_config_id_int:
            user_permission = await permission_service.get_active_permission(
                permission.user_id, api_config_id_int
            )
            if not user_permission:
                logger.warning(f"User {permission.user_id} has no permission for API {api_id}")
                return self._error(f"你没有该 API 的使用权限，请联系管理员授权。API: {api_id}")

            # 从数据库获取完整的API配置（含认证信息）
            db_api_config = await permission_service.get_api_with_auth(api_config_id_int)

        # 如果数据库中没有配置，回退到文件配置
        if not db_api_config:
            registry = get_api_registry()
            user_apis = registry.get_apis_for_user(permission.user_id)
            api_config = user_apis.get(api_id)

            if not api_config:
                available = list(user_apis.keys())
                return self._error(f"未找到API配置: {api_id}。可用的API: {available}")

            if not api_config.enabled:
                return self._error(f"API {api_id} 已禁用")

            # 使用文件配置的API
            return await self._execute_with_file_config(
                api_id, endpoint_name, request_params, path_params,
                api_config, permission
            )

        # 检查API是否激活
        if not db_api_config.get("is_active"):
            return self._error(f"API {api_id} 已禁用")

        # 获取端点配置
        endpoints = db_api_config.get("endpoints", {})
        endpoint_config = endpoints.get(endpoint_name)
        if not endpoint_config:
            available = list(endpoints.keys())
            return self._error(
                f"API {api_id} 没有端点: {endpoint_name}。可用端点: {available}"
            )

        # 检查必需参数
        required_params = endpoint_config.get("required_params", [])
        default_params = endpoint_config.get("default_params", {})
        missing_params = [
            p for p in required_params
            if p not in request_params and p not in path_params and p not in default_params
        ]
        if missing_params:
            return self._error(f"缺少必需参数: {missing_params}")

        # ==================== 执行API调用 ====================
        start_time = time.time()
        status = "success"
        error_message = None

        try:
            # URL 构建逻辑
            base_url = db_api_config.get("base_url", "")
            if not base_url:
                return self._error(f"API {api_id} 缺少 base_url 配置")

            base_url = self._resolve_env_vars(base_url)
            path = endpoint_config.get("path", "")

            # 统一参数源
            all_available_params = {**request_params, **path_params}
            consumed_params = set()

            # 替换路径中的 {placeholder}
            placeholders = re.findall(r'\{([^}]+)\}', path)
            for key in placeholders:
                if key in all_available_params:
                    val = all_available_params[key]
                    path = path.replace(f"{{{key}}}", str(val))
                    consumed_params.add(key)

            # 检查未替换的占位符
            remaining = re.findall(r'\{([^}]+)\}', path)
            if remaining:
                return self._error(f"API 路径参数缺失: {remaining}")

            url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

            # 构建查询参数
            reserved_keys = {"api_id", "endpoint", "params", "path_params", "tool", "parameters", "url", "method", "headers", "body"}
            query_params = dict(default_params)
            params_mapping = endpoint_config.get("params_mapping", {})
            for user_key, user_value in request_params.items():
                if user_key in consumed_params or user_key in reserved_keys:
                    continue
                api_key = params_mapping.get(user_key, user_key)
                query_params[api_key] = user_value

            # 构建请求头（应用认证）
            headers = {}
            auth_config = db_api_config.get("auth_config", {})
            auth_type = db_api_config.get("auth_type", "none")

            if auth_config:
                self._apply_db_auth(headers, auth_type, auth_config)

            # 获取session并发送请求
            session = await self._get_session()
            method = endpoint_config.get("method", "GET").upper()

            logger.info(f"[APIFetch] Calling {method} {url} with params: {query_params}")

            if method == "GET":
                async with session.get(
                    url, headers=headers, params=query_params
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        status = "failed"
                        error_message = f"HTTP {response.status}"
                        return self._error(f"API请求失败: HTTP {response.status} - {text[:200]}")
                    try:
                        data = await response.json(content_type=None)
                        logger.info(f"[APIFetch] Response data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                    except Exception:
                        text = await response.text()
                        status = "failed"
                        error_message = "Non-JSON response"
                        return self._error(f"API返回非JSON格式，响应内容: {text[:200]}")
            elif method == "POST":
                async with session.post(
                    url, headers=headers, params=query_params,
                    json=params.get("body")
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        status = "failed"
                        error_message = f"HTTP {response.status}"
                        return self._error(f"API请求失败: HTTP {response.status}")
                    try:
                        data = await response.json(content_type=None)
                    except Exception:
                        text = await response.text()
                        status = "failed"
                        error_message = "Non-JSON response"
                        return self._error(f"API返回非JSON格式，响应内容: {text[:200]}")
            else:
                return self._error(f"不支持的HTTP方法: {method}")

            # 提取数据路径
            response_data_path = endpoint_config.get("response_data_path")
            if response_data_path:
                data = self._extract_data_path(data, response_data_path)

            # 应用字段映射
            response_field_mapping = endpoint_config.get("response_field_mapping", {})
            if response_field_mapping:
                data = self._apply_field_mapping(data, response_field_mapping)

            # 股票API特殊处理：规范化时间序列数据
            if api_id == "alpha_vantage_stock" and isinstance(data, dict):
                logger.info(f"[APIFetch] Normalizing stock data, input keys: {list(data.keys())}")
                data = self._normalize_stock_data(data)
                logger.info(f"[APIFetch] Normalized data: row_count={data.get('row_count', 0)}")

            return self._success(
                data=data,
                metadata={
                    "api_id": api_id,
                    "endpoint": endpoint_name,
                    "url": url,
                    "method": method,
                }
            )

        except aiohttp.ClientError as e:
            status = "failed"
            error_message = str(e)
            return self._error(f"API请求失败: {str(e)}")
        except Exception as e:
            status = "failed"
            error_message = str(e)
            return self._error(f"API调用异常: {str(e)}")
        finally:
            # 记录API调用日志
            response_time_ms = int((time.time() - start_time) * 1000)
            try:
                await permission_service.log_api_call(
                    user_id=permission.user_id,
                    api_config_id=api_config_id_int,
                    conversation_id=getattr(permission, 'conversation_id', None),
                    status=status,
                    response_time_ms=response_time_ms,
                    error_message=error_message
                )
            except Exception as log_error:
                logger.error(f"Failed to log API call: {log_error}")

    async def _execute_with_file_config(
        self, api_id: str, endpoint_name: str,
        request_params: Dict, path_params: Dict,
        api_config, permission: PermissionContext
    ) -> ToolResult:
        """使用文件配置执行API调用（向后兼容）"""
        endpoint_config = api_config.endpoints.get(endpoint_name)
        if not endpoint_config:
            available = list(api_config.endpoints.keys())
            return self._error(
                f"API {api_id} 没有端点: {endpoint_name}。可用端点: {available}"
            )

        missing_params = [
            p for p in endpoint_config.required_params
            if p not in request_params and p not in path_params and p not in endpoint_config.default_params
        ]
        if missing_params:
            return self._error(f"缺少必需参数: {missing_params}")

        try:
            base_url = self._resolve_env_vars(api_config.base_url)
            path = endpoint_config.path

            all_available_params = {**request_params, **path_params}
            consumed_params = set()

            placeholders = re.findall(r'\{([^}]+)\}', path)
            for key in placeholders:
                if key in all_available_params:
                    val = all_available_params[key]
                    path = path.replace(f"{{{key}}}", str(val))
                    consumed_params.add(key)

            remaining = re.findall(r'\{([^}]+)\}', path)
            if remaining:
                return self._error(f"API 路径参数缺失: {remaining}")

            url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"

            reserved_keys = {"api_id", "endpoint", "params", "path_params", "tool", "parameters", "url", "method", "headers", "body"}
            query_params = dict(endpoint_config.default_params)
            for user_key, user_value in request_params.items():
                if user_key in consumed_params or user_key in reserved_keys:
                    continue
                api_key = endpoint_config.params_mapping.get(user_key, user_key)
                query_params[api_key] = user_value

            headers = dict(api_config.auth.custom_headers)
            self._apply_auth(headers, api_config.auth)

            session = await self._get_session()

            method = endpoint_config.method.upper()
            if method == "GET":
                async with session.get(
                    url, headers=headers, params=query_params
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        return self._error(f"API请求失败: HTTP {response.status} - {text[:200]}")
                    try:
                        data = await response.json(content_type=None)
                    except Exception:
                        text = await response.text()
                        return self._error(f"API返回非JSON格式，响应内容: {text[:200]}")
            elif method == "POST":
                async with session.post(
                    url, headers=headers, params=query_params,
                    json=request_params.get("body")
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        return self._error(f"API请求失败: HTTP {response.status}")
                    try:
                        data = await response.json(content_type=None)
                    except Exception:
                        text = await response.text()
                        return self._error(f"API返回非JSON格式，响应内容: {text[:200]}")
            else:
                return self._error(f"不支持的HTTP方法: {method}")

            if endpoint_config.response_data_path:
                data = self._extract_data_path(data, endpoint_config.response_data_path)

            if endpoint_config.response_field_mapping:
                data = self._apply_field_mapping(data, endpoint_config.response_field_mapping)

            return self._success(
                data=data,
                metadata={
                    "api_id": api_id,
                    "endpoint": endpoint_name,
                    "url": url,
                    "method": method,
                }
            )

        except aiohttp.ClientError as e:
            return self._error(f"API请求失败: {str(e)}")
        except Exception as e:
            return self._error(f"API调用异常: {str(e)}")

    async def _execute_direct_url(
        self,
        params: Dict[str, Any],
        permission: PermissionContext,
    ) -> ToolResult:
        """执行直接URL调用"""
        url = params.get("url")
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        query_params = params.get("params", {})
        body = params.get("body")

        try:
            session = await self._get_session()

            if method == "GET":
                async with session.get(
                    url, headers=headers, params=query_params
                ) as response:
                    if response.status >= 400:
                        return self._error(f"HTTP错误: {response.status}")
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        data = await response.json()
                    else:
                        data = {"text": await response.text()}
            elif method == "POST":
                async with session.post(
                    url, headers=headers, params=query_params, json=body
                ) as response:
                    if response.status >= 400:
                        return self._error(f"HTTP错误: {response.status}")
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        data = await response.json()
                    else:
                        data = {"text": await response.text()}
            else:
                return self._error(f"不支持的HTTP方法: {method}")

            return self._success(
                data=data,
                metadata={"url": url, "method": method}
            )

        except aiohttp.ClientError as e:
            return self._error(f"HTTP错误: {str(e)}")
        except Exception as e:
            return self._error(f"请求失败: {str(e)}")

    def _resolve_env_vars(self, value: str) -> str:
        """解析环境变量 ${VAR_NAME:default}"""
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'

        def replace(match):
            var_name = match.group(1)
            default = match.group(2) or ""
            return os.getenv(var_name, default)

        return re.sub(pattern, replace, value)

    def _apply_auth(self, headers: Dict[str, str], auth_config):
        """应用认证配置（文件配置模式）"""
        if auth_config.type == AuthType.API_KEY:
            key_value = self._resolve_env_vars(auth_config.api_key_value or "")
            if key_value:
                headers[auth_config.api_key_header] = key_value

        elif auth_config.type == AuthType.BEARER_TOKEN:
            token = self._resolve_env_vars(auth_config.bearer_token or "")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif auth_config.type == AuthType.BASIC_AUTH:
            credentials = base64.b64encode(
                f"{auth_config.username}:{auth_config.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

    def _apply_db_auth(self, headers: Dict[str, str], auth_type: str, auth_config: Dict[str, Any]):
        """应用认证配置（数据库配置模式）"""
        if auth_type == "api_key":
            header_name = auth_config.get("api_key_header", "X-API-Key")
            key_value = auth_config.get("api_key_value", "")
            if key_value:
                headers[header_name] = key_value

        elif auth_type == "bearer":
            token = auth_config.get("bearer_token", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif auth_type == "basic":
            username = auth_config.get("username", "")
            password = auth_config.get("password", "")
            if username and password:
                credentials = base64.b64encode(
                    f"{username}:{password}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {credentials}"

        elif auth_type == "custom":
            # 自定义headers
            custom_headers = auth_config.get("custom_headers", {})
            for key, value in custom_headers.items():
                headers[key] = value

    def _extract_data_path(self, data: Any, path: str) -> Any:
        """从响应中提取指定路径的数据"""
        keys = path.split(".")
        result = data
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            elif isinstance(result, list) and key.isdigit():
                result = result[int(key)]
            else:
                return data  # 路径不存在，返回原始数据
        return result

    def _apply_field_mapping(self, data: Any, mapping: Dict[str, str]) -> Any:
        """应用字段映射"""
        if isinstance(data, dict):
            return {mapping.get(k, k): v for k, v in data.items()}
        elif isinstance(data, list):
            return [self._apply_field_mapping(item, mapping) for item in data]
        return data

    def _normalize_stock_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """规范化股票API返回数据为Analyzer可消费的格式"""
        # 检查是否是错误响应
        if "Information" in data or "Error Message" in data or "Note" in data:
            error_msg = data.get("Information") or data.get("Error Message") or data.get("Note")
            logger.warning(f"[APIFetch] Alpha Vantage API error: {error_msg}")
            return {
                "rows": [],
                "row_count": 0,
                "source": "alpha_vantage",
                "error": error_msg,
                "raw_summary": str(data)[:200]
            }

        time_series_key = None
        for key in data.keys():
            if "Time Series" in key:
                time_series_key = key
                break

        if not time_series_key:
            return {
                "rows": [],
                "row_count": 0,
                "source": "alpha_vantage",
                "error": "未找到时间序列数据",
                "raw_summary": str(data)[:200]
            }

        time_series = data[time_series_key]
        rows = []

        for date_str, values in time_series.items():
            row = {"date": date_str}
            for k, v in values.items():
                clean_key = k.split(". ")[-1] if ". " in k else k
                try:
                    row[clean_key] = float(v)
                except (ValueError, TypeError):
                    row[clean_key] = v

            if "close" in row and "open" in row and row["open"] != 0:
                row["pct_change"] = ((row["close"] - row["open"]) / row["open"]) * 100

            rows.append(row)

        rows.sort(key=lambda x: x["date"], reverse=True)

        return {
            "rows": rows,
            "row_count": len(rows),
            "source": "alpha_vantage",
            "symbol": data.get("Meta Data", {}).get("2. Symbol", "Unknown"),
            "raw_summary": f"Retrieved {len(rows)} trading days"
        }

    async def close(self):
        """关闭HTTP客户端"""
        if self._session and not self._session.closed:
            await self._session.close()


# 全局实例
_api_fetch_tool: Optional[APIFetchTool] = None


def get_api_fetch_tool() -> APIFetchTool:
    """获取API Fetch Tool实例"""
    global _api_fetch_tool
    if _api_fetch_tool is None:
        _api_fetch_tool = APIFetchTool()
    return _api_fetch_tool