"""CIA 登录认证 API"""
from typing import Dict, Any
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, status

from app.config.settings import settings
from app.services.cia_service import get_cia_service
from app.services.user_service import get_user_service
from app.api.v1.auth import create_access_token
from app.utils.logger import get_logger

router = APIRouter(prefix="/auth/cia", tags=["cia-auth"])
logger = get_logger()


@router.get("/login")
async def cia_login(code: str, auth_code: str = "") -> Dict[str, Any]:
    """
    CIA 登录回调接口
    前端通过 SDK 获取 code + auth_code 后，调用此接口完成登录
    """
    if not settings.CIA_ENABLED:
        raise HTTPException(status_code=503, detail="CIA 登录未启用")

    # Step 1: code + auth_code -> access_token
    cia = get_cia_service()
    token_res = cia.code_to_token(code, auth_code)
    if not token_res.get("result"):
        # Fallback 1: try without auth_code
        if auth_code:
            logger.warning(f"CIA code_to_token failed with auth_code, trying without: {token_res}")
            token_res = cia.code_to_token(code, "")
        # Fallback 2: try code_login (CIA SDK internal API)
        if not token_res.get("result"):
            logger.warning(f"CIA code_to_token failed, trying code_login: {token_res}")
            token_res = cia.code_login(code)
        if not token_res.get("result"):
            raise HTTPException(
                status_code=400,
                detail=f"CIA 认证失败: {token_res.get('message', token_res.get('errorCode', 'unknown'))}",
            )

    cia_token = token_res["access_token"]

    # Step 2: access_token -> user_info
    user_info = cia.get_user_info(cia_token)
    email = user_info.get("email")
    if not email:
        # 尝试用 mobile 作为备选标识
        email = user_info.get("mobile")
        if not email:
            cia.logout(cia_token)
            raise HTTPException(status_code=400, detail="无法获取 CIA 用户信息（email/mobile 为空）")

    # Step 3: 查找或创建本地用户
    user_service = get_user_service()
    user = user_service.get_user_by_email(email)

    if not user:
        # 自动建号（方案 A）
        user_id = f"cia_{uuid.uuid4().hex[:8]}"
        login_id = email.split("@")[0] if "@" in email else email
        # 避免 login_id 冲突，添加前缀
        existing = user_service.get_user(login_id)
        if existing:
            login_id = f"cia_{login_id}_{uuid.uuid4().hex[:4]}"

        user = user_service.create_user(
            login_id=login_id,
            user_data={
                "user_id": user_id,
                "username": email,  # Use CIA account (email) as display name
                "email": email,
                "phone": user_info.get("mobile"),
                "avatar_url": user_info.get("headPicture"),
                "role": "employee",
                "auth_type": "cia",
                "password": "!cia_no_local_login",  # 标记为 CIA 用户，禁止本地登录
            }
        )
        logger.info(f"CIA auto-provisioned user: {email} -> {login_id}")
    else:
        # 检查账号是否被禁用
        if not user.is_active:
            raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")
        # 更新 CIA 用户信息（头像、手机号等可能变化）
        update_data = {}
        if user_info.get("headPicture") and user_info["headPicture"] != (user.avatar_url or ""):
            update_data["avatar_url"] = user_info["headPicture"]
        if user_info.get("mobile") and user_info["mobile"] != (user.phone or ""):
            update_data["phone"] = user_info["mobile"]
        if email and email != user.username:
            update_data["username"] = email  # Keep username synced with CIA account
        if update_data:
            user_service.update_user(user.login_id, update_data)
            logger.info(f"CIA user updated: {email}")

    # Step 4: 签发本地 JWT
    access_token = create_access_token(data={
        "sub": user.user_id,
        "username": user.username,
        "login_id": user.login_id,
        "email": user.email or email,
        "auth_type": "cia"
    })

    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email or email,
                "role": user.role,
                "avatar_url": user.avatar_url,
                "auth_type": "cia",
            },
            "quota": {
                "daily_limit": user.quota.daily_limit,
                "current_balance": user.quota.current_balance,
                "is_unlimited": user.has_unlimited_credits(),
            }
        }
    }


@router.get("/token")
async def cia_token_exchange(access_token: str) -> Dict[str, Any]:
    """
    用 CIA access_token 直接换取本地 JWT
    前端通过 codeLogin API 获取 CIA token 后调用此接口
    """
    if not settings.CIA_ENABLED:
        raise HTTPException(status_code=503, detail="CIA 登录未启用")

    cia = get_cia_service()

    # Step 1: validate token and get user info
    user_info = cia.get_user_info(access_token)
    email = user_info.get("email")
    if not email:
        email = user_info.get("mobile")
        if not email:
            raise HTTPException(status_code=400, detail="无法获取 CIA 用户信息（email/mobile 为空）")

    # Step 2: find or create local user (same logic as cia_login)
    user_service = get_user_service()
    user = user_service.get_user_by_email(email)

    if not user:
        user_id = f"cia_{uuid.uuid4().hex[:8]}"
        login_id = email.split("@")[0] if "@" in email else email
        existing = user_service.get_user(login_id)
        if existing:
            login_id = f"cia_{login_id}_{uuid.uuid4().hex[:4]}"
        user = user_service.create_user(
            login_id=login_id,
            user_data={
                "user_id": user_id,
                "username": email,  # Use CIA account (email) as display name
                "email": email,
                "phone": user_info.get("mobile"),
                "avatar_url": user_info.get("headPicture"),
                "role": "employee",
                "auth_type": "cia",
                "password": "!cia_no_local_login",
            }
        )
        logger.info(f"CIA auto-provisioned user (token exchange): {email} -> {login_id}")
    else:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")
        update_data = {}
        if user_info.get("headPicture") and user_info["headPicture"] != (user.avatar_url or ""):
            update_data["avatar_url"] = user_info["headPicture"]
        if user_info.get("mobile") and user_info["mobile"] != (user.phone or ""):
            update_data["phone"] = user_info["mobile"]
        if email and email != user.username:
            update_data["username"] = email  # Keep username synced with CIA account
        if update_data:
            user_service.update_user(user.login_id, update_data)
            logger.info(f"CIA user updated (token exchange): {email}")

    # Step 3: issue local JWT
    local_token = create_access_token(data={
        "sub": user.user_id,
        "username": user.username,
        "login_id": user.login_id,
        "email": user.email or email,
        "auth_type": "cia"
    })

    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "access_token": local_token,
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email or email,
                "role": user.role,
                "avatar_url": user.avatar_url,
                "auth_type": "cia",
            },
            "quota": {
                "daily_limit": user.quota.daily_limit,
                "current_balance": user.quota.current_balance,
                "is_unlimited": user.has_unlimited_credits(),
            }
        }
    }


@router.post("/userinfo")
async def cia_userinfo_exchange(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    直接用 CIA 用户信息换取本地 JWT（绕过 findUserWithToken 403 问题）
    前端通过 codeLogin 获取用户信息后调用此接口
    """
    if not settings.CIA_ENABLED:
        raise HTTPException(status_code=503, detail="CIA 登录未启用")

    # Extract user info from codeLogin response
    user_info = body.get("userInfo", body)
    
    # Try email first, then mobile
    email = user_info.get("email") or user_info.get("mobile") or user_info.get("phone")
    if not email:
        # Try other possible fields
        email = user_info.get("username") or user_info.get("loginId") or user_info.get("userId")
        if not email:
            raise HTTPException(status_code=400, detail="无法获取 CIA 用户信息（email/mobile 为空）")

    # Step 2: find or create local user
    user_service = get_user_service()
    user = user_service.get_user_by_email(email)

    if not user:
        user_id = f"cia_{uuid.uuid4().hex[:8]}"
        login_id = email.split("@")[0] if "@" in email else email
        existing = user_service.get_user(login_id)
        if existing:
            login_id = f"cia_{login_id}_{uuid.uuid4().hex[:4]}"
        user = user_service.create_user(
            login_id=login_id,
            user_data={
                "user_id": user_id,
                "username": email,  # Use CIA account (email) as display name
                "email": email,
                "phone": user_info.get("mobile") or user_info.get("phone"),
                "avatar_url": user_info.get("headPicture") or user_info.get("avatar"),
                "role": "employee",
                "auth_type": "cia",
                "password": "!cia_no_local_login",
            }
        )
        logger.info(f"CIA auto-provisioned user (userinfo exchange): {email} -> {login_id}")
    else:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="账号已被禁用，请联系管理员")
        update_data = {}
        avatar = user_info.get("headPicture") or user_info.get("avatar")
        if avatar and avatar != (user.avatar_url or ""):
            update_data["avatar_url"] = avatar
        phone = user_info.get("mobile") or user_info.get("phone")
        if phone and phone != (user.phone or ""):
            update_data["phone"] = phone
        if email and email != user.username:
            update_data["username"] = email  # Keep username synced with CIA account
        if update_data:
            user_service.update_user(user.login_id, update_data)
            logger.info(f"CIA user updated (userinfo exchange): {email}")

    # Step 3: issue local JWT
    local_token = create_access_token(data={
        "sub": user.user_id,
        "username": user.username,
        "login_id": user.login_id,
        "email": user.email or email,
        "auth_type": "cia"
    })

    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            "access_token": local_token,
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email or email,
                "role": user.role,
                "avatar_url": user.avatar_url,
                "auth_type": "cia",
            },
            "quota": {
                "daily_limit": user.quota.daily_limit,
                "current_balance": user.quota.current_balance,
                "is_unlimited": user.has_unlimited_credits(),
            }
        }
    }


@router.get("/config")
async def cia_config() -> Dict[str, Any]:
    """获取 CIA 登录配置（供前端使用）"""
    return {
        "enabled": settings.CIA_ENABLED,
        "client_id": settings.CIA_ACCESS_CLIENT_ID,
        "auth_mode": settings.AUTH_MODE,
        "cia_url": settings.CIA_URL,
    }
