"""
API Configuration - 通用API配置管理
支持灵活配置各种外部API
Storage: MySQL/PostgreSQL database
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
import asyncio

from sqlalchemy import select
from app.access.database.connection import get_db
from app.access.database.models import ApiConfig as ApiConfigDB, UserApiConfig as UserApiConfigDB


class AuthType(str, Enum):
    """API认证类型"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer"
    BASIC_AUTH = "basic"
    CUSTOM = "custom"


class APIAuthConfig(BaseModel):
    """API认证配置"""
    type: AuthType = AuthType.NONE
    # API Key认证
    api_key_header: str = "X-API-Key"  # API Key放在哪个header
    api_key_value: Optional[str] = None  # API Key值
    # Bearer Token认证
    bearer_token: Optional[str] = None
    # Basic Auth
    username: Optional[str] = None
    password: Optional[str] = None
    # 自定义headers
    custom_headers: Dict[str, str] = Field(default_factory=dict)


class APIEndpointConfig(BaseModel):
    """API端点配置"""
    path: str = ""  # 端点路径
    method: str = "GET"  # HTTP方法
    description: str = ""  # 端点描述

    # 参数映射：用户参数名 -> API参数名
    params_mapping: Dict[str, str] = Field(default_factory=dict)

    # 必需参数
    required_params: List[str] = Field(default_factory=list)

    # 默认参数值
    default_params: Dict[str, Any] = Field(default_factory=dict)

    # 参数描述
    params_descriptions: Dict[str, str] = Field(default_factory=dict)

    # 响应数据路径：从响应中提取数据的JSONPath
    response_data_path: Optional[str] = None  # 如: "data.list" 或 "result.items"

    # 响应字段映射：API字段名 -> 显示字段名
    response_field_mapping: Dict[str, str] = Field(default_factory=dict)


class APIConfig(BaseModel):
    """单个API配置"""
    name: str  # API名称
    description: str = ""  # API描述
    base_url: str  # 基础URL
    auth: APIAuthConfig = Field(default_factory=APIAuthConfig)
    endpoints: Dict[str, APIEndpointConfig] = Field(default_factory=dict)

    # 是否启用
    enabled: bool = True

    # 超时设置
    timeout: int = 30

    # 重试次数
    retry_count: int = 3

    # 是否为系统默认配置（不可删除）
    is_system: bool = False

    # 推荐问题列表
    recommended_questions: List[str] = Field(default_factory=list)


class APIRegistry:
    """API注册表 - 管理所有API配置
    Storage: Database
    """

    def __init__(self):
        self._db = None
        self._system_apis: Dict[str, APIConfig] = {}
        self._load_system_apis()
        # Also load DB APIs into _system_apis so they're available for suggestion generation
        try:
            all_apis = self.list_apis()
            for api_id, api_config in all_apis.items():
                if api_id not in self._system_apis:
                    self._system_apis[api_id] = api_config
        except Exception as e:
            logger.error(f"Failed to load DB APIs on startup: {e}")

    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return asyncio.run(coro)

    async def _get_db(self):
        """Get database connection."""
        if self._db is None:
            self._db = await get_db()
        return self._db

    def _load_system_apis(self):
        """加载系统默认API配置（硬编码）"""
        # IP地理位置API - 系统默认API
        self._system_apis["geo"] = APIConfig(
            name="IP地理位置API",
            description="查询IP地址的地理位置信息，包括国家、省份、城市、运营商、经纬度等",
            base_url="https://api.example.com",
            auth=APIAuthConfig(
                type=AuthType.NONE
            ),
            endpoints={
                "ip_lookup": APIEndpointConfig(
                    path="/api/iplocaltion",
                    method="GET",
                    description="查询IP地理位置",
                    params_mapping={
                        "ip": "ip"
                    },
                    required_params=["ip"],
                    response_data_path="data"
                )
            },
            is_system=True
        )

    def _db_to_pydantic(self, db_config: ApiConfigDB) -> APIConfig:
        """Convert database model to Pydantic model."""
        # auth_config can be: None, dict, or encrypted string
        auth_data = db_config.auth_config or {}
        if isinstance(auth_data, str):
            auth_data = {}
        auth_config = APIAuthConfig(
            type=AuthType(auth_data.get("type", "none")),
            api_key_header=auth_data.get("api_key_header", "X-API-Key"),
            api_key_value=auth_data.get("api_key_value"),
            bearer_token=auth_data.get("bearer_token"),
            username=auth_data.get("username"),
            password=auth_data.get("password"),
            custom_headers=auth_data.get("custom_headers", {})
        )

        # endpoints can be: None, dict, or JSON string
        endpoints_data = db_config.endpoints or {}
        if isinstance(endpoints_data, str):
            import json
            try:
                endpoints_data = json.loads(endpoints_data)
            except json.JSONDecodeError:
                endpoints_data = {}

        endpoints = {}
        for ep_name, ep_data in endpoints_data.items():
            endpoints[ep_name] = APIEndpointConfig(
                path=ep_data.get("path", ""),
                method=ep_data.get("method", "GET"),
                description=ep_data.get("description", ""),
                params_mapping=ep_data.get("params_mapping", {}),
                required_params=ep_data.get("required_params", []),
                default_params=ep_data.get("default_params", {}),
                params_descriptions=ep_data.get("params_descriptions", {}),
                response_data_path=ep_data.get("response_data_path"),
                response_field_mapping=ep_data.get("response_field_mapping", {})
            )

        return APIConfig(
            name=db_config.name,
            description=db_config.description or "",
            base_url=db_config.base_url or "",
            auth=auth_config,
            endpoints=endpoints,
            enabled=db_config.is_active,
            timeout=db_config.timeout,
            retry_count=db_config.retry_count,
            is_system=db_config.is_system,
            recommended_questions=db_config.recommended_questions or []
        )

    def _pydantic_to_db_dict(self, api_id: str, config: APIConfig, created_by: int = None) -> dict:
        """Convert Pydantic model to database dict."""
        return {
            "config_id": api_id,
            "name": config.name,
            "description": config.description,
            "base_url": config.base_url,
            "auth_type": config.auth.type.value,
            "auth_config": config.auth.model_dump(),
            "endpoints": {k: v.model_dump() for k, v in config.endpoints.items()},
            "timeout": config.timeout,
            "retry_count": config.retry_count,
            "is_system": config.is_system,
            "is_active": config.enabled,
            "created_by": created_by,
            "recommended_questions": config.recommended_questions if config.recommended_questions else None
        }

    def register_api(self, api_id: str, config: APIConfig, persist: bool = True):
        """注册API配置"""
        return self._run_async(self._register_api_async(api_id, config, persist))

    async def _register_api_async(self, api_id: str, config: APIConfig, persist: bool = True):
        """注册API配置到数据库"""
        if config.is_system:
            # 系统API只存在内存中
            self._system_apis[api_id] = config
            return

        if not persist:
            return

        db = await self._get_db()
        async with db.get_session() as session:
            # Check if exists
            result = await session.execute(
                select(ApiConfigDB).where(ApiConfigDB.config_id == api_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update
                for key, value in self._pydantic_to_db_dict(api_id, config).items():
                    if key != "config_id":  # Don't update primary key
                        setattr(existing, key, value)
            else:
                # Create
                db_config = ApiConfigDB(**self._pydantic_to_db_dict(api_id, config))
                session.add(db_config)

            await session.commit()

    def delete_api(self, api_id: str) -> bool:
        """删除API配置"""
        return self._run_async(self._delete_api_async(api_id))

    async def _delete_api_async(self, api_id: str) -> bool:
        """删除API配置从数据库"""
        # Check system APIs
        if api_id in self._system_apis:
            return False  # Cannot delete system API

        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(ApiConfigDB).where(ApiConfigDB.config_id == api_id)
            )
            db_config = result.scalar_one_or_none()

            if not db_config:
                return False

            if db_config.is_system:
                return False

            await session.delete(db_config)
            await session.commit()
            return True

    def update_api(self, api_id: str, config: APIConfig) -> bool:
        """更新API配置"""
        return self._run_async(self._update_api_async(api_id, config))

    async def _update_api_async(self, api_id: str, config: APIConfig) -> bool:
        """更新API配置到数据库"""
        if config.is_system:
            self._system_apis[api_id] = config
            return True

        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(ApiConfigDB).where(ApiConfigDB.config_id == api_id)
            )
            db_config = result.scalar_one_or_none()

            if not db_config:
                # Create new
                db_config = ApiConfigDB(**self._pydantic_to_db_dict(api_id, config))
                session.add(db_config)
            else:
                # Update existing
                for key, value in self._pydantic_to_db_dict(api_id, config).items():
                    if key != "config_id":
                        setattr(db_config, key, value)

            await session.commit()
            return True

    def get_api(self, api_id: str) -> Optional[APIConfig]:
        """获取API配置"""
        return self._run_async(self._get_api_async(api_id))

    async def _get_api_async(self, api_id: str) -> Optional[APIConfig]:
        """获取API配置从数据库"""
        # Check system APIs first
        if api_id in self._system_apis:
            return self._system_apis[api_id]

        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(ApiConfigDB).where(
                    ApiConfigDB.config_id == api_id,
                    ApiConfigDB.is_active == True
                )
            )
            db_config = result.scalar_one_or_none()

            if not db_config:
                return None

            return self._db_to_pydantic(db_config)

    def list_apis(self) -> Dict[str, APIConfig]:
        """列出所有API"""
        return self._run_async(self._list_apis_async())

    async def _list_apis_async(self) -> Dict[str, APIConfig]:
        """列出所有API从数据库"""
        result = dict(self._system_apis)  # Start with system APIs

        db = await self._get_db()
        async with db.get_session() as session:
            db_result = await session.execute(
                select(ApiConfigDB).where(ApiConfigDB.is_active == True)
            )
            db_configs = db_result.scalars().all()

            for db_config in db_configs:
                if db_config.config_id not in result:  # Don't override system APIs
                    result[db_config.config_id] = self._db_to_pydantic(db_config)

        return result

    def get_enabled_apis(self) -> Dict[str, APIConfig]:
        """获取所有启用的API"""
        return self._run_async(self._get_enabled_apis_async())

    async def _get_enabled_apis_async(self) -> Dict[str, APIConfig]:
        """获取所有启用的API"""
        result = dict(self._system_apis)  # System APIs are always enabled

        db = await self._get_db()
        async with db.get_session() as session:
            db_result = await session.execute(
                select(ApiConfigDB).where(ApiConfigDB.is_active == True)
            )
            db_configs = db_result.scalars().all()

            for db_config in db_configs:
                if db_config.is_active and db_config.config_id not in result:
                    result[db_config.config_id] = self._db_to_pydantic(db_config)

        return result

    def get_api_description(self) -> str:
        """获取所有API的描述（用于LLM提示）"""
        apis = self._run_async(self._get_enabled_apis_async())
        descriptions = []
        for api_id, api in apis.items():
            endpoints_desc = []
            for ep_name, ep in api.endpoints.items():
                params = ", ".join(ep.params_mapping.keys()) if ep.params_mapping else "无参数"
                endpoints_desc.append(f"    - {ep_name}: {ep.description} (参数: {params})")

            descriptions.append(f"""
API [{api_id}] - {api.name}
  描述: {api.description}
  端点:
{chr(10).join(endpoints_desc)}
""")
        return "\n".join(descriptions)

    # ==================== User-Level API Management ====================

    def load_user_custom_apis(self, user_id: str) -> Dict[str, APIConfig]:
        """Load user's custom APIs from database."""
        return self._run_async(self._load_user_custom_apis_async(user_id))

    async def _load_user_custom_apis_async(self, user_id: str) -> Dict[str, APIConfig]:
        """Load user's custom APIs from database."""
        result = {}
        db = await self._get_db()

        async with db.get_session() as session:
            db_result = await session.execute(
                select(UserApiConfigDB).where(UserApiConfigDB.user_id == user_id)
            )
            user_configs = db_result.scalars().all()

            for user_config in user_configs:
                if user_config.custom_config:
                    config_data = user_config.custom_config
                    api_id = user_config.api_config_id or str(user_config.id)

                    auth_data = config_data.get("auth", {})
                    auth_config = APIAuthConfig(
                        type=AuthType(auth_data.get("type", "none")),
                        api_key_header=auth_data.get("api_key_header", "X-API-Key"),
                        api_key_value=auth_data.get("api_key_value"),
                        bearer_token=auth_data.get("bearer_token"),
                        username=auth_data.get("username"),
                        password=auth_data.get("password"),
                        custom_headers=auth_data.get("custom_headers", {})
                    )

                    endpoints = {}
                    for ep_name, ep_data in config_data.get("endpoints", {}).items():
                        endpoints[ep_name] = APIEndpointConfig(
                            path=ep_data.get("path", ""),
                            method=ep_data.get("method", "GET"),
                            description=ep_data.get("description", ""),
                            params_mapping=ep_data.get("params_mapping", {}),
                            required_params=ep_data.get("required_params", []),
                            default_params=ep_data.get("default_params", {}),
                            response_data_path=ep_data.get("response_data_path"),
                            response_field_mapping=ep_data.get("response_field_mapping", {})
                        )

                    result[api_id] = APIConfig(
                        name=config_data.get("name", api_id),
                        description=config_data.get("description", ""),
                        base_url=config_data.get("base_url", ""),
                        auth=auth_config,
                        endpoints=endpoints,
                        enabled=config_data.get("enabled", True),
                        timeout=config_data.get("timeout", 30),
                        retry_count=config_data.get("retry_count", 3),
                        is_system=False
                    )

        return result

    def save_user_custom_apis(self, user_id: str, apis: Dict[str, APIConfig]):
        """Save user's custom APIs to database."""
        return self._run_async(self._save_user_custom_apis_async(user_id, apis))

    async def _save_user_custom_apis_async(self, user_id: str, apis: Dict[str, APIConfig]):
        """Save user's custom APIs to database."""
        db = await self._get_db()

        async with db.get_session() as session:
            # Delete existing user APIs
            db_result = await session.execute(
                select(UserApiConfigDB).where(UserApiConfigDB.user_id == user_id)
            )
            existing = db_result.scalars().all()
            for config in existing:
                await session.delete(config)

            # Add new APIs
            for api_id, config in apis.items():
                db_config = UserApiConfigDB(
                    user_id=user_id,
                    api_config_id=api_id,
                    custom_config={
                        "name": config.name,
                        "description": config.description,
                        "base_url": config.base_url,
                        "auth": config.auth.model_dump(),
                        "endpoints": {k: v.model_dump() for k, v in config.endpoints.items()},
                        "enabled": config.enabled,
                        "timeout": config.timeout,
                        "retry_count": config.retry_count
                    }
                )
                session.add(db_config)

            await session.commit()

    def get_apis_for_user(self, user_id: str) -> Dict[str, APIConfig]:
        """
        Get all APIs accessible by a user.
        Returns system APIs + user's custom APIs.
        """
        return self._run_async(self._get_apis_for_user_async(user_id))

    async def _get_apis_for_user_async(self, user_id: str) -> Dict[str, APIConfig]:
        """Get all APIs accessible by a user from database."""
        # Start with system APIs
        result = dict(self._system_apis)

        # Add user's custom APIs
        user_apis = await self._load_user_custom_apis_async(user_id)
        result.update(user_apis)

        return result

    def get_permitted_apis_for_user(self, user_id: str, role: str) -> Dict[str, APIConfig]:
        """
        Get APIs that the user has active permission for.
        Admin users get all APIs; non-admin users are filtered by user_api_permissions.
        """
        return self._run_async(self._get_permitted_apis_for_user_async(user_id, role))

    async def _get_permitted_apis_for_user_async(self, user_id: str, role: str) -> Dict[str, APIConfig]:
        """Get permitted APIs for a user from database.
        Queries user_api_permissions by user_id (not login_id) for consistency
        with grant_permissions/revoke_permissions in api_permission_service.
        """
        if role == "admin":
            return dict(self._system_apis)

        db = await self._get_db()
        async with db.get_session() as session:
            from app.access.database.models import UserAPIPermission, APIConfig as ApiConfigDB
            from sqlalchemy import select, and_

            # Query directly by user_id (same key used in grant_permissions)
            result = await session.execute(
                select(ApiConfigDB)
                .join(UserAPIPermission, ApiConfigDB.id == UserAPIPermission.api_config_id)
                .where(
                    and_(
                        UserAPIPermission.user_id == user_id,
                        UserAPIPermission.status == "active"
                    )
                )
            )
            db_configs = result.scalars().all()

            permitted = {}
            for db_config in db_configs:
                config_id = db_config.config_id
                if config_id not in permitted:
                    permitted[config_id] = self._db_to_pydantic(db_config)

            return permitted

    def register_user_api(self, user_id: str, api_id: str, config: APIConfig) -> bool:
        """Register a custom API for a specific user."""
        return self._run_async(self._register_user_api_async(user_id, api_id, config))

    async def _register_user_api_async(self, user_id: str, api_id: str, config: APIConfig) -> bool:
        """Register a custom API for a specific user in database."""
        if config.is_system:
            return False  # Cannot create system API for user

        db = await self._get_db()

        async with db.get_session() as session:
            # Check if already exists
            db_result = await session.execute(
                select(UserApiConfigDB).where(
                    UserApiConfigDB.user_id == user_id,
                    UserApiConfigDB.api_config_id == api_id
                )
            )
            existing = db_result.scalar_one_or_none()

            custom_config = {
                "name": config.name,
                "description": config.description,
                "base_url": config.base_url,
                "auth": config.auth.model_dump(),
                "endpoints": {k: v.model_dump() for k, v in config.endpoints.items()},
                "enabled": config.enabled,
                "timeout": config.timeout,
                "retry_count": config.retry_count
            }

            if existing:
                existing.custom_config = custom_config
            else:
                db_config = UserApiConfigDB(
                    user_id=user_id,
                    api_config_id=api_id,
                    custom_config=custom_config
                )
                session.add(db_config)

            await session.commit()
            return True

    def delete_user_api(self, user_id: str, api_id: str) -> bool:
        """Delete a custom API for a specific user."""
        return self._run_async(self._delete_user_api_async(user_id, api_id))

    async def _delete_user_api_async(self, user_id: str, api_id: str) -> bool:
        """Delete a custom API for a specific user from database."""
        db = await self._get_db()

        async with db.get_session() as session:
            db_result = await session.execute(
                select(UserApiConfigDB).where(
                    UserApiConfigDB.user_id == user_id,
                    UserApiConfigDB.api_config_id == api_id
                )
            )
            existing = db_result.scalar_one_or_none()

            if not existing:
                return False

            await session.delete(existing)
            await session.commit()
            return True

    def update_user_api(self, user_id: str, api_id: str, config: APIConfig) -> bool:
        """Update a custom API for a specific user."""
        return self._run_async(self._update_user_api_async(user_id, api_id, config))

    async def _update_user_api_async(self, user_id: str, api_id: str, config: APIConfig) -> bool:
        """Update a custom API for a specific user in database."""
        return await self._register_user_api_async(user_id, api_id, config)


# 全局API注册表实例
_api_registry: Optional[APIRegistry] = None


def get_api_registry() -> APIRegistry:
    """获取API注册表实例"""
    global _api_registry
    if _api_registry is None:
        _api_registry = APIRegistry()
    return _api_registry


def reload_api_registry():
    """重新加载API配置"""
    global _api_registry
    _api_registry = APIRegistry()
    return _api_registry