"""
Pydantic models for API Permission System request/response schemas.

IMPORTANT: APIConfigPublic does NOT include auth_config field to ensure
sensitive authentication data is never exposed to non-admin users.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


# ==================== Enums ====================

class PermissionStatus(str, Enum):
    """API permission status."""
    PENDING = "pending"
    ACTIVE = "active"
    DISABLED = "disabled"


class AuthType(str, Enum):
    """API authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    CUSTOM = "custom"


# ==================== Category Models ====================

class CategoryBase(BaseModel):
    """Base category model."""
    name: str = Field(..., description="分类名称", max_length=200)
    description: Optional[str] = Field(None, description="分类描述")
    parent_id: Optional[int] = Field(None, description="父分类ID")
    sort_order: int = Field(0, description="排序顺序")


class CategoryCreate(CategoryBase):
    """Category creation request."""
    pass


class CategoryUpdate(BaseModel):
    """Category update request."""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class CategoryResponse(CategoryBase):
    """Category response with full details."""
    id: int
    created_at: datetime
    updated_at: datetime
    api_count: int = Field(0, description="该分类下的 API 数量")

    class Config:
        from_attributes = True


class CategoryTreeNode(CategoryResponse):
    """Category with children for tree display."""
    children: List["CategoryTreeNode"] = Field(default_factory=list)


# ==================== API Config Models ====================

class EndpointConfig(BaseModel):
    """API endpoint configuration."""
    path: str = ""
    method: str = "GET"
    description: str = ""
    params_mapping: Dict[str, str] = Field(default_factory=dict)
    required_params: List[str] = Field(default_factory=list)
    default_params: Dict[str, Any] = Field(default_factory=dict)
    params_descriptions: Dict[str, str] = Field(default_factory=dict)
    response_data_path: Optional[str] = None
    response_field_mapping: Dict[str, str] = Field(default_factory=dict)


class AuthConfigInput(BaseModel):
    """
    Auth configuration for API creation/update.
    This model is used for INPUT only - admins provide auth config.
    """
    type: AuthType = AuthType.NONE
    api_key_header: str = "X-API-Key"
    api_key_value: Optional[str] = None
    bearer_token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    custom_headers: Dict[str, str] = Field(default_factory=dict)


class APIConfigCreate(BaseModel):
    """API creation request (admin only)."""
    config_id: str = Field(..., description="API 唯一标识", max_length=100)
    name: str = Field(..., description="API 名称", max_length=200)
    description: Optional[str] = Field(None, description="API 描述")
    base_url: str = Field(..., description="基础 URL", max_length=500)
    category_id: Optional[int] = Field(None, description="分类 ID")
    auth: Optional[AuthConfigInput] = Field(None, description="认证配置")
    endpoints: Dict[str, EndpointConfig] = Field(default_factory=dict, description="端点配置")
    timeout: int = Field(30, ge=1, le=300, description="超时时间(秒)")
    retry_count: int = Field(3, ge=0, le=10, description="重试次数")
    is_active: bool = Field(True, description="是否启用")
    recommended_questions: Optional[List[str]] = Field(None, description="推荐问题列表")


class APIConfigUpdate(BaseModel):
    """API update request (admin only)."""
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    base_url: Optional[str] = Field(None, max_length=500)
    category_id: Optional[int] = None
    auth: Optional[AuthConfigInput] = None
    endpoints: Optional[Dict[str, EndpointConfig]] = None
    timeout: Optional[int] = Field(None, ge=1, le=300)
    retry_count: Optional[int] = Field(None, ge=0, le=10)
    is_active: Optional[bool] = None
    recommended_questions: Optional[List[str]] = Field(None, description="推荐问题列表")


class APIConfigPublic(BaseModel):
    """
    API configuration visible to regular users.
    IMPORTANT: This model does NOT include auth_config field!
    Use this for /my-apis endpoint to ensure auth data is never exposed.
    """
    id: int
    config_id: str
    name: str
    description: Optional[str] = None
    base_url: Optional[str] = None  # Some systems may want to hide this too
    auth_type: Optional[str] = Field(None, description="认证类型")
    category_id: Optional[int] = None
    category_path: Optional[str] = Field(None, description="分类完整路径")
    is_active: bool
    endpoints: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 30
    recommended_questions: Optional[List[str]] = Field(None, description="推荐问题列表")

    class Config:
        from_attributes = True


class APIConfigAdmin(BaseModel):
    """
    Full API configuration for admin view.
    Includes auth_config but with sensitive values masked.
    """
    id: int
    config_id: str
    name: str
    description: Optional[str] = None
    base_url: Optional[str] = None
    category_id: Optional[int] = None
    category_path: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = Field(
        None,
        description="认证配置（敏感值已脱敏）"
    )
    endpoints: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 30
    retry_count: int = 3
    is_system: bool = False
    is_active: bool
    recommended_questions: Optional[List[str]] = Field(None, description="推荐问题列表")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Permission Models ====================

class PermissionGrant(BaseModel):
    """Permission grant request."""
    user_id: str = Field(..., description="用户 ID")
    api_config_ids: List[int] = Field(..., description="API 配置 ID 列表")


class PermissionRevoke(BaseModel):
    """Permission revoke request."""
    user_id: str = Field(..., description="用户 ID")
    api_config_ids: List[int] = Field(..., description="API 配置 ID 列表")


class BatchPermissionGrant(BaseModel):
    """Batch permission grant request - multiple APIs to multiple users."""
    api_ids: List[int] = Field(..., description="API 配置 ID 列表")
    user_ids: List[str] = Field(..., description="用户 ID 列表")


class BatchPermissionRevoke(BaseModel):
    """Batch permission revoke request - by permission IDs."""
    permission_ids: List[int] = Field(..., description="权限记录 ID 列表")


class BatchCategorize(BaseModel):
    """Batch categorize APIs request."""
    api_ids: List[int] = Field(..., description="API 配置 ID 列表")
    category_id: Optional[int] = Field(None, description="目标分类 ID (null=取消分类)")


class UserSearchResponse(BaseModel):
    """User search result."""
    id: int
    user_id: str
    username: str
    role: str


class UserPermissionResponse(BaseModel):
    """User's API permission details."""
    id: int
    user_id: str
    api_config_id: int
    api_name: str = Field(..., description="API 名称")
    api_description: Optional[str] = None
    status: str
    granted_at: Optional[datetime] = None
    granted_by: Optional[int] = None

    class Config:
        from_attributes = True


class APIGrantedUserResponse(BaseModel):
    """Users who have access to an API."""
    user_id: str
    username: str
    status: str
    granted_at: Optional[datetime] = None
    department: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Overview Models ====================

class UserPermissionSummary(BaseModel):
    """Summary of a user's permissions."""
    user_id: str
    username: str
    department: Optional[str] = None
    api_count: int = 0


class APIPermissionSummary(BaseModel):
    """Summary of an API's permissions."""
    api_id: int
    api_name: str
    user_count: int = 0
    call_count_7d: int = 0


class APICallLogResponse(BaseModel):
    """API call log entry."""
    id: int
    user_id: Optional[str] = None
    api_config_id: Optional[int] = None
    api_name: Optional[str] = None
    conversation_id: Optional[str] = None
    status: Optional[str] = None
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    called_at: datetime

    class Config:
        from_attributes = True


class PermissionOverview(BaseModel):
    """Full permission overview for admin dashboard."""
    total_apis: int
    active_apis: int
    total_users_with_permissions: int
    by_user: List[UserPermissionSummary] = Field(default_factory=list)
    by_api: List[APIPermissionSummary] = Field(default_factory=list)
    recent_calls: List[APICallLogResponse] = Field(default_factory=list)


# ==================== Response Wrappers ====================

class MessageResponse(BaseModel):
    """Generic message response."""
    success: bool
    message: str
    detail: Optional[str] = None


class CategoryListResponse(BaseModel):
    """List of categories."""
    categories: List[CategoryResponse]
    total: int


class APIListResponse(BaseModel):
    """List of APIs (admin view)."""
    apis: List[APIConfigAdmin]
    total: int


class MyAPIListResponse(BaseModel):
    """
    List of APIs for regular user.
    IMPORTANT: Uses APIConfigPublic which excludes auth_config.
    """
    apis: List[APIConfigPublic]
    total: int


class PermissionListResponse(BaseModel):
    """List of user permissions."""
    permissions: List[UserPermissionResponse]
    total: int


class GrantedUserListResponse(BaseModel):
    """List of users granted to an API."""
    users: List[APIGrantedUserResponse]
    total: int