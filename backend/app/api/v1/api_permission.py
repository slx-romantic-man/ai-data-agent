"""
API Permission Routes - API权限管理接口
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from pydantic import BaseModel

from app.models.user import UserContext
from app.models.api_permission import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryTreeNode,
    CategoryListResponse,
    APIConfigCreate, APIConfigUpdate, APIConfigAdmin,
    APIListResponse, MyAPIListResponse,
    PermissionGrant, PermissionRevoke,
    PermissionListResponse, GrantedUserListResponse,
    PermissionOverview, MessageResponse
)
from app.services.api_permission_service import (
    get_api_permission_service, APIPermissionService
)
from app.api.dependencies import get_user_context, require_admin
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api-permission", tags=["API Permission"])


# ==================== Request/Response Models ====================

class BatchGrantRequest(BaseModel):
    """批量授权请求"""
    api_ids: List[int]
    user_ids: List[str]


class BatchRevokeRequest(BaseModel):
    """批量撤销权限请求"""
    permission_ids: List[int]


class BatchCategorizeRequest(BaseModel):
    """批量分类请求"""
    api_ids: List[int]
    category_id: Optional[int] = None


class BatchOperationResponse(BaseModel):
    """批量操作响应"""
    success: bool
    success_count: int
    failed: List[dict]
    message: str


class UserSearchResponse(BaseModel):
    """用户搜索响应"""
    users: List[dict]
    total: int


class UncategorizedAPIResponse(BaseModel):
    """未分类API响应"""
    apis: List[dict]
    total: int


class UserPermissionOverviewResponse(BaseModel):
    """用户权限概览响应"""
    user_id: str
    username: str
    role: str
    total_permissions: int
    categorized: List[dict]
    uncategorized: List[dict]


# ==================== Category Routes ====================

@router.get("/categories/tree", response_model=CategoryListResponse)
async def get_category_tree(
    user: UserContext = Depends(get_user_context)
):
    """获取 API 分类树"""
    service = await get_api_permission_service()
    tree = await service.get_category_tree()
    # Flatten tree for response
    def flatten(nodes):
        result = []
        for node in nodes:
            result.append(CategoryResponse.model_validate(node))
            result.extend(flatten(node.children))
        return result
    all_categories = flatten(tree)
    return CategoryListResponse(categories=all_categories, total=len(all_categories))


@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    user: UserContext = Depends(require_admin)
):
    """创建 API 分类（管理员）"""
    service = await get_api_permission_service()
    try:
        return await service.create_category(
            name=data.name,
            description=data.description,
            parent_id=data.parent_id
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    user: UserContext = Depends(require_admin)
):
    """更新 API 分类（管理员）"""
    service = await get_api_permission_service()
    result = await service.update_category(
        category_id,
        **data.model_dump(exclude_unset=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="分类不存在")
    return result


@router.delete("/categories/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int,
    user: UserContext = Depends(require_admin)
):
    """删除 API 分类（管理员）"""
    service = await get_api_permission_service()
    try:
        success = await service.delete_category(category_id)
        if not success:
            raise HTTPException(status_code=404, detail="分类不存在")
        return MessageResponse(success=True, message="分类已删除")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== System API Routes ====================

@router.get("/system-apis", response_model=APIListResponse)
async def list_system_apis(
    category_id: Optional[int] = Query(None, description="按分类筛选"),
    user: UserContext = Depends(require_admin)
):
    """获取所有 API 配置列表（管理员）"""
    service = await get_api_permission_service()
    apis = await service.get_all_apis(category_id=category_id, include_auth=True)
    return APIListResponse(apis=apis, total=len(apis))


@router.get("/system-apis/uncategorized", response_model=UncategorizedAPIResponse)
async def get_uncategorized_apis(
    user: UserContext = Depends(require_admin)
):
    """获取未分类的API列表（管理员）"""
    service = await get_api_permission_service()
    apis = await service.get_uncategorized_apis()
    return UncategorizedAPIResponse(apis=apis, total=len(apis))


@router.get("/system-apis/{api_id:int}", response_model=APIConfigAdmin)
async def get_system_api(
    api_id: int,
    user: UserContext = Depends(require_admin)
):
    """获取单个 API 配置详情（管理员）"""
    service = await get_api_permission_service()
    api = await service.get_api_by_id(api_id)
    if not api:
        raise HTTPException(status_code=404, detail="API 不存在")
    return api


@router.post("/system-apis", response_model=APIConfigAdmin)
async def create_system_api(
    data: APIConfigCreate,
    user: UserContext = Depends(require_admin)
):
    """创建 API 配置（管理员）"""
    service = await get_api_permission_service()
    try:
        # admin_id from user context (using user_id as int if numeric)
        admin_id = 1  # Default for demo
        return await service.create_api(admin_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/system-apis/{api_id}", response_model=APIConfigAdmin)
async def update_system_api(
    api_id: int,
    data: APIConfigUpdate,
    user: UserContext = Depends(require_admin)
):
    """更新 API 配置（管理员）"""
    service = await get_api_permission_service()
    result = await service.update_api(api_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="API 不存在")
    return result


@router.delete("/system-apis/{api_id}", response_model=MessageResponse)
async def delete_system_api(
    api_id: int,
    user: UserContext = Depends(require_admin)
):
    """删除 API 配置（管理员）"""
    service = await get_api_permission_service()
    success = await service.delete_api(api_id)
    if not success:
        raise HTTPException(status_code=404, detail="API 不存在")
    return MessageResponse(success=True, message="API 已删除")


# ==================== Permission Routes ====================

@router.get("/permissions/overview", response_model=PermissionOverview)
async def get_permissions_overview(
    user: UserContext = Depends(require_admin)
):
    """获取权限概览（管理员）"""
    service = await get_api_permission_service()
    return await service.get_permissions_overview()


@router.get("/permissions/user/{user_id}", response_model=PermissionListResponse)
async def get_user_permissions(
    user_id: str,
    user: UserContext = Depends(require_admin)
):
    """获取用户的 API 权限列表（管理员）"""
    service = await get_api_permission_service()
    permissions = await service.get_user_permissions(user_id)
    return PermissionListResponse(permissions=permissions, total=len(permissions))


@router.get("/permissions/api/{api_id}", response_model=GrantedUserListResponse)
async def get_api_granted_users(
    api_id: int,
    user: UserContext = Depends(require_admin)
):
    """获取被授权某 API 的用户列表（管理员）"""
    service = await get_api_permission_service()
    users = await service.get_api_granted_users(api_id)
    return GrantedUserListResponse(users=users, total=len(users))


@router.post("/permissions/grant", response_model=MessageResponse)
async def grant_permissions(
    data: PermissionGrant,
    user: UserContext = Depends(require_admin)
):
    """授权 API 权限给用户（管理员）"""
    service = await get_api_permission_service()
    admin_id = 1  # Default for demo
    result = await service.grant_permissions(
        admin_id=admin_id,
        user_id=data.user_id,
        api_config_ids=data.api_config_ids
    )
    return MessageResponse(
        success=True,
        message=f"已授权 {len(result['granted'])} 个 API，"
                f"重新激活 {len(result['reactivated'])} 个，"
                f"跳过 {len(result['skipped'])} 个"
    )


@router.post("/permissions/revoke", response_model=MessageResponse)
async def revoke_permissions(
    data: PermissionRevoke,
    user: UserContext = Depends(require_admin)
):
    """撤销用户的 API 权限（管理员）"""
    service = await get_api_permission_service()
    admin_id = 1  # Default for demo
    result = await service.revoke_permissions(
        admin_id=admin_id,
        user_id=data.user_id,
        api_config_ids=data.api_config_ids
    )
    return MessageResponse(
        success=True,
        message=f"已撤销 {len(result['revoked'])} 个权限，"
                f"未找到 {len(result['not_found'])} 个"
    )


# ==================== User Routes ====================

@router.get("/my-apis", response_model=MyAPIListResponse)
async def get_my_apis(
    user: UserContext = Depends(get_user_context)
):
    """
    获取当前用户有权限的 API 列表
    IMPORTANT: 不返回 auth_config 字段
    """
    service = await get_api_permission_service()
    apis = await service.get_my_apis(user.user_id)
    return MyAPIListResponse(apis=apis, total=len(apis))


# ==================== Embedding Routes ====================

@router.post("/system-apis/rebuild-embeddings", response_model=MessageResponse)
async def rebuild_embeddings(
    user: UserContext = Depends(require_admin)
):
    """
    重建所有API的向量索引（管理员）
    用于在API配置变更后更新向量检索索引
    """
    try:
        from app.services.api_retrieval_service import get_api_retrieval_service
        retrieval_service = get_api_retrieval_service()
        result = await retrieval_service.rebuild_all_embeddings()
        return MessageResponse(
            success=True,
            message=f"重建完成: 成功 {result['success']} 个, 失败 {result['failure']} 个"
        )
    except Exception as e:
        logger.error(f"Failed to rebuild embeddings: {e}")
        return MessageResponse(
            success=False,
            message=f"重建失败: {str(e)}"
        )


# ==================== Batch Operation Routes ====================

@router.post("/permissions/batch-grant", response_model=BatchOperationResponse)
async def batch_grant_permissions(
    data: BatchGrantRequest,
    user: UserContext = Depends(require_admin)
):
    """批量授权：多个API授权给多个用户（管理员）"""
    service = await get_api_permission_service()
    try:
        result = await service.batch_grant_permissions(
            admin_id=int(user.user_id) if str(user.user_id).isdigit() else 1,
            api_ids=data.api_ids,
            user_ids=data.user_ids
        )
        return BatchOperationResponse(
            success=result["success"] > 0,
            success_count=result["success"],
            failed=[d for d in result.get("details", []) if d.get("action") == "failed"],
            message=f"成功授权 {result['success']} 个，失败 {result['failure']} 个"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/permissions/batch-revoke", response_model=BatchOperationResponse)
async def batch_revoke_permissions(
    data: BatchRevokeRequest,
    user: UserContext = Depends(require_admin)
):
    """批量撤销权限（管理员）"""
    service = await get_api_permission_service()
    try:
        result = await service.batch_revoke_permissions(
            admin_id=int(user.user_id) if str(user.user_id).isdigit() else 1,
            permission_ids=data.permission_ids
        )
        return BatchOperationResponse(
            success=result["success"] > 0,
            success_count=result["success"],
            failed=[] if result["failure"] == 0 else [{"error": "部分权限撤销失败"}],
            message=f"成功撤销 {result['success']} 个权限，失败 {result['failure']} 个"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/search", response_model=UserSearchResponse)
async def search_users(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(50, description="返回数量限制"),
    user: UserContext = Depends(require_admin)
):
    """搜索用户（管理员）"""
    service = await get_api_permission_service()
    users = await service.search_users(query=q, limit=limit)
    return UserSearchResponse(users=users, total=len(users))


@router.post("/system-apis/batch-categorize", response_model=BatchOperationResponse)
async def batch_categorize_apis(
    data: BatchCategorizeRequest,
    user: UserContext = Depends(require_admin)
):
    """批量分类API（管理员）"""
    service = await get_api_permission_service()
    try:
        result = await service.batch_categorize_apis(
            api_ids=data.api_ids,
            category_id=data.category_id,
        )
        action = "分类" if data.category_id else "取消分类"
        return BatchOperationResponse(
            success=result["success"] > 0,
            success_count=result["success"],
            failed=[] if result["failure"] == 0 else [{"error": "部分API分类失败"}],
            message=f"成功{action} {result['success']} 个API，失败 {result['failure']} 个"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/{user_id}/permission-overview", response_model=UserPermissionOverviewResponse)
async def get_user_permission_overview(
    user_id: str,
    user: UserContext = Depends(require_admin)
):
    """获取用户权限概览（管理员）"""
    service = await get_api_permission_service()
    try:
        overview = await service.get_user_permission_overview(user_id)
        return UserPermissionOverviewResponse(**overview)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))