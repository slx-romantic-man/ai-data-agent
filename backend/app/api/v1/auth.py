"""
Authentication API endpoints.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

from app.config.settings import settings
from app.models.user import UserContext, UserRegister
from app.api.dependencies import get_user_context
from app.utils.logger import get_logger
from app.utils.helpers import generate_session_id
from app.services.user_service import get_user_service


router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Dict[str, Any]:
    """
    Login and get access token.

    Demo credentials:
    - admin/admin123 (admin role, unlimited credits)
    - user1/user123 (employee role, 100 credits/day)
    - manager1/manager123 (manager role, 100 credits/day)
    """
    user_service = get_user_service()

    # Get user by login ID
    user = user_service.get_user(form_data.username)

    if not user or user.password != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check and reset quota if new day
    user_service.check_and_reset_if_needed(form_data.username)

    # Create access token
    access_token = create_access_token(
        data={"sub": user.user_id, "username": user.username, "login_id": form_data.username}
    )

    # Get quota info
    quota_info = {
        "daily_limit": user.quota.daily_limit,
        "current_balance": user.quota.current_balance,
        "last_reset": user.quota.last_reset.isoformat(),
        "is_unlimited": user.has_unlimited_credits()
    }

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "department": user.department,
            "business_line": user.business_line,
        },
        "quota": quota_info
    }


@router.get("/me")
async def get_current_user_info(
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """Get current user information."""
    return {
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role,
        "data_scope": user.data_scope,
        "department": user.department,
        "business_line": user.business_line,
    }


@router.get("/quota")
async def get_quota_info(
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """Get current user's quota information."""
    from app.services.user_service import get_user_service

    user_service = get_user_service()
    user_account = user_service.get_user_by_user_id(user.user_id)

    if not user_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check and reset quota if new day
    user_service.check_and_reset_if_needed(user_account.user_id)

    return {
        "daily_limit": user_account.quota.daily_limit,
        "current_balance": user_account.quota.current_balance,
        "last_reset": user_account.quota.last_reset.isoformat(),
        "is_unlimited": user_account.has_unlimited_credits()
    }


@router.get("/permissions")
async def get_permissions(
    user: UserContext = Depends(get_user_context),
) -> Dict[str, Any]:
    """Get user's permissions."""
    return {
        "user_id": user.user_id,
        "role": user.role,
        "data_scope": user.data_scope,
        "permissions": user.permissions,
        "filters": user.filters,
    }


@router.post("/logout")
async def logout(
    user: UserContext = Depends(get_user_context),
) -> Dict[str, str]:
    """Logout current user."""
    # In production, invalidate the token
    return {"status": "logged_out"}


@router.post("/register")
async def register(
    user_data: UserRegister,
) -> Dict[str, Any]:
    """
    Register a new user.

    New users get employee role with 100 daily credits.
    """
    user_service = get_user_service()

    # Generate unique user_id
    user_id = f"user_{generate_session_id()[:8]}"

    try:
        new_user = user_service.create_user(
            login_id=user_data.login_id,
            user_data={
                "user_id": user_id,
                "username": user_data.username,
                "password": user_data.password,
                "role": "employee",  # New users default to employee
            }
        )
        return {
            "status": "success",
            "user_id": new_user.user_id,
            "message": "注册成功",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )