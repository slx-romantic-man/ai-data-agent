"""
API Management Endpoints - API配置管理接口
支持用户级别的API隔离
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from app.config.api_config import (
    get_api_registry, APIConfig, APIAuthConfig, APIEndpointConfig, AuthType
)
from app.models.user import UserContext
from app.api.dependencies import get_user_context
from app.services.api_permission_service import get_api_permission_service

router = APIRouter(prefix="/apis", tags=["API Management"])


# Request/Response Models
class EndpointConfigModel(BaseModel):
    """端点配置模型"""
    path: str = ""
    method: str = "GET"
    description: str = ""
    params_mapping: Dict[str, str] = Field(default_factory=dict)
    required_params: List[str] = Field(default_factory=list)
    default_params: Dict[str, Any] = Field(default_factory=dict)
    response_data_path: Optional[str] = None
    response_field_mapping: Dict[str, str] = Field(default_factory=dict)


class AuthConfigModel(BaseModel):
    """认证配置模型"""
    type: str = "none"
    api_key_header: str = "X-API-Key"
    api_key_value: Optional[str] = None
    bearer_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    custom_headers: Dict[str, str] = Field(default_factory=dict)


class APICreateRequest(BaseModel):
    """创建API请求模型"""
    id: str = Field(...,
                    description="API唯一标识，只能包含小写字母、数字和下划线")
    name: str = Field(..., description="API显示名称")
    description: str = Field(default="", description="API功能描述")
    base_url: str = Field(...,
                          description="API基础URL，如 https://api.example.com")
    auth: AuthConfigModel = Field(default_factory=AuthConfigModel)
    endpoints: Dict[str, EndpointConfigModel] = Field(default_factory=dict)
    enabled: bool = True
    timeout: int = 30
    retry_count: int = 3


class APIUpdateRequest(BaseModel):
    """更新API请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    auth: Optional[AuthConfigModel] = None
    endpoints: Optional[Dict[str, EndpointConfigModel]] = None
    enabled: Optional[bool] = None
    timeout: Optional[int] = None
    retry_count: Optional[int] = None


class APIResponse(BaseModel):
    """API响应模型"""
    id: str
    name: str
    description: str
    base_url: str
    auth: Dict[str, Any]
    endpoints: Dict[str, Any]
    enabled: bool
    is_system: bool = False
    timeout: int
    retry_count: int


@router.get("", response_model=Dict[str, Any])
async def list_apis(user: UserContext = Depends(get_user_context)):
    """获取当前用户可见的API配置列表"""
    if user.role == "admin":
        registry = get_api_registry()
        apis = registry.get_apis_for_user(user.user_id)

        result = []
        for api_id, config in apis.items():
            result.append({
                "id": api_id,
                "name": config.name,
                "description": config.description,
                "base_url": config.base_url,
                "auth": (
                    config.auth.model_dump()
                    if config.auth else {"type": "none"}
                ),
                "endpoints": {
                    k: v.model_dump()
                    for k, v in (config.endpoints or {}).items()
                },
                "enabled": config.enabled,
                "is_system": config.is_system,
                "timeout": config.timeout,
                "retry_count": config.retry_count
            })
        return {"apis": result, "total": len(result)}

    service = await get_api_permission_service()
    my_apis = await service.get_my_apis(user.user_id)
    result = []
    for api_item in my_apis:
        result.append({
            "id": api_item.config_id,
            "config_id": api_item.config_id,
            "name": api_item.name,
            "description": api_item.description,
            "base_url": api_item.base_url,
            "auth": {"type": "none"},
            "endpoints": api_item.endpoints or {},
            "enabled": api_item.is_active,
            "is_system": True,
            "timeout": api_item.timeout,
            "retry_count": 3,
            "category_id": api_item.category_id,
            "category_path": api_item.category_path
        })

    return {"apis": result, "total": len(result)}


@router.get("/{api_id}", response_model=Dict[str, Any])
async def get_api(api_id: str, user: UserContext = Depends(get_user_context)):
    """获取单个API配置详情"""
    if user.role == "admin":
        registry = get_api_registry()
        user_apis = registry.get_apis_for_user(user.user_id)
        config = user_apis.get(api_id)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"API {api_id} not found"
            )

        return {
            "id": api_id,
            "name": config.name,
            "description": config.description,
            "base_url": config.base_url,
            "auth": config.auth.model_dump() if config.auth else {},
            "endpoints": {
                k: v.model_dump()
                for k, v in (config.endpoints or {}).items()
            },
            "enabled": config.enabled,
            "is_system": config.is_system,
            "timeout": config.timeout,
            "retry_count": config.retry_count
        }

    service = await get_api_permission_service()
    my_apis = await service.get_my_apis(user.user_id)

    matched = None
    for item in my_apis:
        if item.config_id == api_id or str(item.id) == api_id:
            matched = item
            break

    if not matched:
        raise HTTPException(
            status_code=404,
            detail=f"API {api_id} not found"
        )

    return {
        "id": matched.config_id,
        "config_id": matched.config_id,
        "name": matched.name,
        "description": matched.description,
        "base_url": matched.base_url,
        "auth": {"type": "none"},
        "endpoints": matched.endpoints or {},
        "enabled": matched.is_active,
        "is_system": True,
        "timeout": matched.timeout,
        "retry_count": 3,
        "category_id": matched.category_id,
        "category_path": matched.category_path
    }


@router.post("", response_model=Dict[str, Any])
async def create_api(
        request: APICreateRequest,
        user: UserContext = Depends(get_user_context)):
    """创建新的API配置（保存到当前用户的私有配置）"""
    import re

    # 验证API ID格式
    if not re.match(r'^[a-z][a-z0-9_]*$', request.id):
        raise HTTPException(
            status_code=400,
            detail="API ID格式错误：只能包含小写字母、数字和下划线，"
                   "且必须以字母开头"
        )

    registry = get_api_registry()

    # Check if API already exists in user's APIs or system APIs
    user_apis = registry.get_apis_for_user(user.user_id)
    if request.id in user_apis:
        raise HTTPException(status_code=400, detail=f"API {request.id} already exists")

    # Convert auth model
    auth_type = AuthType.NONE
    if request.auth.type == "api_key":
        auth_type = AuthType.API_KEY
    elif request.auth.type == "bearer":
        auth_type = AuthType.BEARER_TOKEN
    elif request.auth.type == "basic":
        auth_type = AuthType.BASIC_AUTH
    elif request.auth.type == "custom":
        auth_type = AuthType.CUSTOM

    auth_config = APIAuthConfig(
        type=auth_type,
        api_key_header=request.auth.api_key_header,
        api_key_value=request.auth.api_key_value,
        bearer_token=request.auth.bearer_token,
        username=request.auth.username,
        password=request.auth.password,
        custom_headers=request.auth.custom_headers
    )

    # Convert endpoints
    endpoints = {}
    for ep_name, ep_config in request.endpoints.items():
        endpoints[ep_name] = APIEndpointConfig(
            path=ep_config.path,
            method=ep_config.method,
            description=ep_config.description,
            params_mapping=ep_config.params_mapping,
            required_params=ep_config.required_params,
            default_params=ep_config.default_params,
            response_data_path=ep_config.response_data_path,
            response_field_mapping=ep_config.response_field_mapping
        )

    # Create API config
    api_config = APIConfig(
        name=request.name,
        description=request.description,
        base_url=request.base_url,
        auth=auth_config,
        endpoints=endpoints,
        enabled=request.enabled,
        timeout=request.timeout,
        retry_count=request.retry_count,
        is_system=False  # 用户创建的API不是系统API
    )

    # Register API for this specific user
    registry.register_user_api(user.user_id, request.id, api_config)

    return {
        "success": True,
        "message": f"API {request.id} created successfully",
        "id": request.id
    }


@router.put("/{api_id}", response_model=Dict[str, Any])
async def update_api(
        api_id: str,
        request: APIUpdateRequest,
        user: UserContext = Depends(get_user_context)):
    """更新API配置（系统API会创建用户副本）"""
    registry = get_api_registry()

    # Get user's APIs
    user_apis = registry.load_user_custom_apis(user.user_id)

    # Check if this is a user's custom API
    if api_id not in user_apis:
        # Check if it's a system API
        system_apis = {k: v for k, v in registry.list_apis().items()
                       if v.is_system}
        if api_id in system_apis:
            # 对于系统API，复制一份到用户自定义API中
            import copy
            system_config = system_apis[api_id]
            # 创建用户副本（深拷贝）
            config = APIConfig(
                name=system_config.name,
                description=system_config.description,
                base_url=system_config.base_url,
                auth=system_config.auth.model_copy() if system_config.auth else APIAuthConfig(),
                endpoints=copy.deepcopy(system_config.endpoints),
                enabled=system_config.enabled,
                timeout=system_config.timeout,
                retry_count=system_config.retry_count,
                is_system=False  # 用户副本不是系统API
            )
        else:
            raise HTTPException(status_code=404, detail=f"API {api_id} not found")
    else:
        config = user_apis[api_id]

    # Update fields
    if request.name is not None:
        config.name = request.name
    if request.description is not None:
        config.description = request.description
    if request.base_url is not None:
        config.base_url = request.base_url
    if request.enabled is not None:
        config.enabled = request.enabled
    if request.timeout is not None:
        config.timeout = request.timeout
    if request.retry_count is not None:
        config.retry_count = request.retry_count

    if request.auth is not None:
        auth_type = AuthType.NONE
        if request.auth.type == "api_key":
            auth_type = AuthType.API_KEY
        elif request.auth.type == "bearer":
            auth_type = AuthType.BEARER_TOKEN
        elif request.auth.type == "basic":
            auth_type = AuthType.BASIC_AUTH
        elif request.auth.type == "custom":
            auth_type = AuthType.CUSTOM

        config.auth = APIAuthConfig(
            type=auth_type,
            api_key_header=request.auth.api_key_header,
            api_key_value=request.auth.api_key_value,
            bearer_token=request.auth.bearer_token,
            username=request.auth.username,
            password=request.auth.password,
            custom_headers=request.auth.custom_headers
        )

    if request.endpoints is not None:
        endpoints = {}
        for ep_name, ep_config in request.endpoints.items():
            endpoints[ep_name] = APIEndpointConfig(
                path=ep_config.path,
                method=ep_config.method,
                description=ep_config.description,
                params_mapping=ep_config.params_mapping,
                required_params=ep_config.required_params,
                default_params=ep_config.default_params,
                response_data_path=ep_config.response_data_path,
                response_field_mapping=ep_config.response_field_mapping
            )
        config.endpoints = endpoints

    # Save changes to user's custom APIs
    user_apis[api_id] = config
    registry.save_user_custom_apis(user.user_id, user_apis)

    return {
        "success": True,
        "message": f"API {api_id} updated successfully"
    }


@router.delete("/{api_id}", response_model=Dict[str, Any])
async def delete_api(
        api_id: str,
        user: UserContext = Depends(get_user_context)):
    """删除API配置（只能删除用户自定义API）"""
    registry = get_api_registry()

    # Check if it's a system API
    system_apis = {k: v for k, v in registry.list_apis().items()
                   if v.is_system}
    if api_id in system_apis:
        raise HTTPException(
            status_code=403,
            detail=f"API {api_id} is a system API and cannot be deleted"
        )

    # Try to delete from user's custom APIs
    success = registry.delete_user_api(user.user_id, api_id)
    if success:
        return {
            "success": True,
            "message": f"API {api_id} deleted successfully"
        }
    else:
        raise HTTPException(
            status_code=404,
            detail=f"API {api_id} not found"
        )


@router.get("/schema/auth-types", response_model=Dict[str, Any])
async def get_auth_types():
    """获取所有支持的认证类型"""
    return {
        "auth_types": [
            {
                "value": "none",
                "label": "无认证",
                "description": "不需要任何认证信息",
                "fields": []
            },
            {
                "value": "api_key",
                "label": "API Key",
                "description": "在请求头中添加API密钥",
                "fields": [
                    {
                        "name": "api_key_header",
                        "label": "Header名称",
                        "default": "X-API-Key",
                        "description": "API Key放在哪个请求头中"
                    },
                    {
                        "name": "api_key_value",
                        "label": "API Key值",
                        "description": "API密钥的值"
                    }
                ]
            },
            {
                "value": "bearer",
                "label": "Bearer Token",
                "description": "使用OAuth 2.0 Bearer Token认证",
                "fields": [
                    {
                        "name": "bearer_token",
                        "label": "Token值",
                        "description": "Bearer Token的值"
                    }
                ]
            },
            {
                "value": "basic",
                "label": "Basic Auth",
                "description": "使用HTTP Basic认证",
                "fields": [
                    {
                        "name": "username",
                        "label": "用户名",
                        "description": "Basic认证用户名"
                    },
                    {
                        "name": "password",
                        "label": "密码",
                        "description": "Basic认证密码"
                    }
                ]
            },
            {
                "value": "custom",
                "label": "自定义Headers",
                "description": "自定义请求头认证",
                "fields": [
                    {
                        "name": "custom_headers",
                        "label": "自定义Headers",
                        "description": "键值对形式的自定义请求头"
                    }
                ]
            }
        ]
    }


@router.get("/schema/http-methods", response_model=Dict[str, Any])
async def get_http_methods():
    """获取支持的HTTP方法"""
    return {
        "methods": [
            {"value": "GET", "label": "GET", "description": "获取资源"},
            {"value": "POST", "label": "POST", "description": "创建资源"},
            {"value": "PUT", "label": "PUT", "description": "更新资源"},
            {"value": "DELETE", "label": "DELETE", "description": "删除资源"},
            {"value": "PATCH", "label": "PATCH", "description": "部分更新资源"}
        ]
    }