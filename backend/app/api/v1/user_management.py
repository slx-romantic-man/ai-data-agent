"""
User Management API endpoints - Admin only endpoints for managing users and viewing all data.
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.models.user import UserContext
from app.api.dependencies import get_user_context
from app.services.user_service import get_user_service
from app.services.credit_service import get_credit_service
from app.services.conversation_service import get_conversation_service
from app.utils.logger import get_logger


router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger()


def require_admin(user: UserContext = Depends(get_user_context)) -> UserContext:
    """Dependency to ensure user is admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return user


class QuotaAdjustRequest(BaseModel):
    """Request model for quota adjustment."""
    amount: int


# ==================== User Management ====================

@router.get("/users")
async def list_users(
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """List all users with their quota status."""
    user_service = get_user_service()
    credit_service = get_credit_service()

    users = user_service.list_users()
    user_list = []

    for user in users:
        # Get usage stats
        stats = credit_service.get_user_usage_stats(user.user_id)

        user_list.append({
            "user_id": user.user_id,
            "login_id": getattr(user, "login_id", user.user_id),
            "username": user.username,
            "role": user.role,
            "department": user.department,
            "business_line": user.business_line,
            "is_active": user.is_active,
            "auth_type": getattr(user, 'auth_type', 'local'),
            "quota": {
                "daily_limit": user.quota.daily_limit,
                "current_balance": user.quota.current_balance,
                "last_reset": user.quota.last_reset.isoformat(),
                "is_unlimited": user.has_unlimited_credits()
            },
            "usage_stats": stats,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat()
        })

    return {
        "users": user_list,
        "total": len(user_list)
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: str,
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """Get detailed user information including usage history."""
    user_service = get_user_service()
    credit_service = get_credit_service()

    user = user_service.get_user_by_user_id(user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Get usage stats
    stats = credit_service.get_user_usage_stats(user_id)

    # Get recent credit logs
    logs = credit_service.get_logs(user_id, limit=20)

    return {
        "user_id": user.user_id,
            "login_id": getattr(user, "login_id", user.user_id),
        "username": user.username,
        "role": user.role,
        "department": user.department,
        "business_line": user.business_line,
        "is_active": user.is_active,
        "auth_type": getattr(user, 'auth_type', 'local'),
        "quota": {
            "daily_limit": user.quota.daily_limit,
            "current_balance": user.quota.current_balance,
            "last_reset": user.quota.last_reset.isoformat(),
            "is_unlimited": user.has_unlimited_credits()
        },
        "usage_stats": stats,
        "recent_logs": [
            {
                "timestamp": log.timestamp.isoformat(),
                "query": log.query,
                "input_tokens": log.input_tokens,
                "output_tokens": log.output_tokens,
                "total_tokens": log.total_tokens,
                "credits_deducted": log.credits_deducted,
                "balance_after": log.balance_after
            }
            for log in logs
        ],
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat()
    }


@router.put("/users/{user_id}/quota")
async def adjust_user_quota(
    user_id: str,
    request: QuotaAdjustRequest,
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """Adjust a user's credit quota. Positive to add, negative to deduct."""
    user_service = get_user_service()

    # Get the login_id from user_id
    login_id = user_service.get_login_id_by_user_id(user_id)
    if not login_id:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    success = user_service.adjust_quota(login_id, request.amount)

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to adjust quota"
        )

    # Get updated user
    user = user_service.get_user_by_user_id(user_id)

    return {
        "status": "success",
        "user_id": user_id,
        "adjustment": request.amount,
        "new_balance": user.quota.current_balance if user else 0
    }


# ==================== Conversation Management ====================

@router.get("/conversations")
async def list_all_conversations(
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """List all conversations from all users."""
    user_service = get_user_service()
    conversation_service = get_conversation_service()

    conversations = conversation_service.get_all_conversations(user_service)

    return {
        "conversations": conversations,
        "total": len(conversations)
    }


@router.get("/conversations/search")
async def search_all_conversations(
    keyword: Optional[str] = Query(None, description="Search keyword"),
    username: Optional[str] = Query(None, description="Filter by username"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """Search all conversations across all users with optional filters."""
    user_service = get_user_service()
    conversation_service = get_conversation_service()

    results = conversation_service.search_all_conversations(
        keyword=keyword,
        user_service=user_service,
        username=username,
        start_date=start_date,
        end_date=end_date
    )

    return {
        "keyword": keyword,
        "username": username,
        "start_date": start_date,
        "end_date": end_date,
        "results": results,
        "total": len(results)
    }


@router.get("/conversations/{user_id}/{session_id}")
async def get_any_conversation(
    user_id: str,
    session_id: str,
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """Get any conversation (admin only)."""
    conversation_service = get_conversation_service()
    user_service = get_user_service()

    conversation = conversation_service.get_conversation(user_id, session_id)

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )

    # Get username
    user = user_service.get_user_by_user_id(user_id)
    username = user.username if user else user_id

    return {
        **conversation,
        "username": username
    }


# ==================== Credit Logs ====================

@router.get("/credit-logs")
async def get_credit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000),
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """Get credit usage logs."""
    credit_service = get_credit_service()
    user_service = get_user_service()

    logs = credit_service.get_logs(user_id, limit)

    # Enrich with username
    log_list = []
    for log in logs:
        user = user_service.get_user_by_user_id(log.user_id)
        log_list.append({
            "timestamp": log.timestamp.isoformat(),
            "user_id": log.user_id,
            "username": user.username if user else log.user_id,
            "session_id": log.session_id,
            "query": log.query,
            "input_tokens": log.input_tokens,
            "output_tokens": log.output_tokens,
            "total_tokens": log.total_tokens,
            "credits_deducted": log.credits_deducted,
            "balance_after": log.balance_after
        })

    return {
        "logs": log_list,
        "total": len(log_list)
    }


# ==================== System Operations ====================

@router.post("/reset-quotas")
async def reset_all_quotas(
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """Manually reset all users' daily quotas."""
    user_service = get_user_service()

    user_service.reset_daily_quotas()

    return {
        "status": "success",
        "message": "All user quotas have been reset"
    }

# ==================== User Status & Delete Operations ====================

class UserStatusRequest(BaseModel):
    """Request model for enabling/disabling a user."""
    is_active: bool


class BatchUserOperationRequest(BaseModel):
    """Request model for batch user operations."""
    user_ids: List[str]


@router.put("/users/{user_id}/status")
async def set_user_status(
    user_id: str,
    request: UserStatusRequest,
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """Enable or disable a user. Admin users cannot be disabled."""
    user_service = get_user_service()

    user = user_service.get_user_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Guard: cannot disable/enable admin users
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot modify admin user status")

    success = user_service.set_user_active(user.login_id, request.is_active)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update user status")

    return {
        "status": "success",
        "user_id": user_id,
        "is_active": request.is_active,
        "message": "User " + ("enabled" if request.is_active else "disabled")
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """Delete a user (hard delete). Admin users cannot be deleted."""
    user_service = get_user_service()

    user = user_service.get_user_by_user_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Guard: cannot delete admin users
    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete admin user")

    success = user_service.delete_user(user.login_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete user")

    return {
        "status": "success",
        "user_id": user_id,
        "message": "User deleted successfully"
    }


@router.post("/users/batch-disable")
async def batch_disable_users(
    request: BatchUserOperationRequest,
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """Batch disable multiple users. Admin users are skipped."""
    user_service = get_user_service()

    results = {"success": [], "skipped": [], "failed": []}
    for user_id in request.user_ids:
        user = user_service.get_user_by_user_id(user_id)
        if not user:
            results["failed"].append({"user_id": user_id, "reason": "User not found"})
            continue
        if user.role == "admin":
            results["skipped"].append({"user_id": user_id, "reason": "Admin user cannot be disabled"})
            continue
        success = user_service.set_user_active(user.login_id, False)
        if success:
            results["success"].append(user_id)
        else:
            results["failed"].append({"user_id": user_id, "reason": "Update failed"})

    return {
        "status": "success",
        "results": results,
        "total": len(request.user_ids),
        "processed": len(results["success"]) + len(results["skipped"]) + len(results["failed"])
    }


@router.post("/users/batch-delete")
async def batch_delete_users(
    request: BatchUserOperationRequest,
    admin: UserContext = Depends(require_admin),
) -> Dict[str, Any]:
    """Batch delete multiple users. Admin users are skipped."""
    user_service = get_user_service()

    results = {"success": [], "skipped": [], "failed": []}
    for user_id in request.user_ids:
        user = user_service.get_user_by_user_id(user_id)
        if not user:
            results["failed"].append({"user_id": user_id, "reason": "User not found"})
            continue
        if user.role == "admin":
            results["skipped"].append({"user_id": user_id, "reason": "Admin user cannot be deleted"})
            continue
        success = user_service.delete_user(user.login_id)
        if success:
            results["success"].append(user_id)
        else:
            results["failed"].append({"user_id": user_id, "reason": "Delete failed"})

    return {
        "status": "success",
        "results": results,
        "total": len(request.user_ids),
        "processed": len(results["success"]) + len(results["skipped"]) + len(results["failed"])
    }
