"""
API Dependencies - Dependency injection for FastAPI.
"""
from typing import Optional
from functools import lru_cache
import json
import base64

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config.settings import settings
from app.models.user import UserContext
from app.models.permission import PermissionContext
from app.agent import get_agent_engine, AgentEngine
from app.access.database import get_db, DatabaseConnection
from app.access.permission import get_rbac_manager, RBACManager
from app.utils.logger import get_logger


security = HTTPBearer(auto_error=False)
logger = get_logger()

# Global cached schema
_cached_schema: str = ""


from jose import JWTError, jwt


def _verify_jwt_token(token: str) -> dict:
    """Verify JWT token signature and return payload."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return {}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserContext:
    """
    Get current user from JWT token using UserService.
    Verifies JWT signature before trusting the payload.
    """
    from app.services.user_service import get_user_service

    if credentials:
        # Verify JWT signature and decode payload
        payload = _verify_jwt_token(credentials.credentials)
        user_id = payload.get("sub") or payload.get("user_id")

        if user_id:
            user_service = get_user_service()
            user_context = user_service.get_user_context(user_id)
            if user_context:
                return user_context

        # Log if user not found
        if user_id:
            logger.warning(f"User not found in UserService: {user_id}")

    # Demo mode disabled in production: do not fallback to default user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_user_context(
    user: UserContext = Depends(get_current_user),
) -> UserContext:
    """Get user context for request processing."""
    return user


async def require_admin(
    user: UserContext = Depends(get_user_context),
) -> UserContext:
    """
    Dependency that requires admin role.
    Raises 403 if user is not an admin.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return user


async def get_permission_context(
    user: UserContext = Depends(get_user_context),
) -> PermissionContext:
    """
    Build permission context from user context.
    This performs permission validation at the API layer.
    """
    rbac_manager = get_rbac_manager()
    permission_context = rbac_manager.build_permission_context(
        user_id=user.user_id,
        role=user.role,
        department=user.department,
        business_line=user.business_line,
        row_filters=user.filters if hasattr(user, 'filters') else None,
    )

    # Validate user has basic read permission
    if not permission_context.has_permission("read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have read permission",
        )

    return permission_context


def validate_export_permission(
    permission: PermissionContext = Depends(get_permission_context),
) -> PermissionContext:
    """
    Validate that user has export permission.
    Use this dependency for export-related endpoints.
    """
    if not permission.has_permission("export"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have export permission",
        )
    return permission


def validate_admin_permission(
    permission: PermissionContext = Depends(get_permission_context),
) -> PermissionContext:
    """
    Validate that user has admin permission.
    Use this dependency for admin-only endpoints.
    """
    if not permission.has_permission("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permission required",
        )
    return permission


@lru_cache()
def get_table_schema() -> str:
    """Get cached table schema for SQL generation."""
    # Demo table schema - includes common tables
    return """
    -- 分类表
    TABLE categories (
        category_id INT PRIMARY KEY,
        category_name VARCHAR(100),
        description TEXT
    );

    -- 客户表
    TABLE customers (
        customer_id VARCHAR(10) PRIMARY KEY,
        company_name VARCHAR(100),
        customer_name VARCHAR(50),
        contact_name VARCHAR(50),
        contact_title VARCHAR(50),
        email VARCHAR(100),
        address VARCHAR(200),
        phone VARCHAR(20),
        city VARCHAR(50),
        region VARCHAR(50),
        postal_code VARCHAR(20),
        country VARCHAR(50),
        fax VARCHAR(20),
        credit_limit DECIMAL(10,2)
    );

    -- 员工表
    TABLE employees (
        employee_id INT PRIMARY KEY,
        name VARCHAR(100),
        first_name VARCHAR(50),
        last_name VARCHAR(50),
        department VARCHAR(50),
        title VARCHAR(50),
        email VARCHAR(100),
        phone_number VARCHAR(20),
        hire_date DATE,
        salary DECIMAL(10,2),
        city VARCHAR(50)
    );

    -- 订单表
    TABLE orders (
        order_id INT PRIMARY KEY,
        customer_id VARCHAR(10),
        employee_id INT,
        order_date DATETIME,
        required_date DATETIME,
        shipped_date DATETIME,
        ship_via INT,
        freight DECIMAL(10,2),
        ship_name VARCHAR(50),
        ship_address VARCHAR(200),
        ship_city VARCHAR(50),
        ship_region VARCHAR(50),
        ship_postal_code VARCHAR(20),
        ship_country VARCHAR(50)
    );

    -- 订单明细表
    TABLE order_items (
        order_id INT,
        order_item_id INT,
        product_id INT,
        quantity INT,
        unit_price DECIMAL(10,2),
        discount DECIMAL(5,2)
    );

    -- 产品表
    TABLE products (
        product_id INT PRIMARY KEY,
        product_name VARCHAR(100),
        supplier_id INT,
        category_id INT,
        quantity_per_unit VARCHAR(50),
        unit_price DECIMAL(10,2),
        units_in_stock INT,
        units_on_order INT,
        discontinued VARCHAR(10)
    );

    -- 供应商表
    TABLE suppliers (
        supplier_id INT PRIMARY KEY,
        company_name VARCHAR(100),
        contact_name VARCHAR(50),
        address VARCHAR(200),
        city VARCHAR(50),
        region VARCHAR(50),
        postal_code VARCHAR(20),
        country VARCHAR(50),
        phone VARCHAR(20)
    );
    """


def set_cached_schema(schema: str):
    """Set the cached schema."""
    global _cached_schema
    _cached_schema = schema


async def get_agent() -> AgentEngine:
    """Get agent engine instance."""
    engine = await get_agent_engine()

    # Use fallback schema (sync, no database calls)
    if not engine._table_schema:
        engine.set_table_schema(get_table_schema())

    return engine


async def get_database() -> DatabaseConnection:
    """Get database connection."""
    return await get_db()


async def get_permission_manager() -> RBACManager:
    """Get RBAC manager."""
    return get_rbac_manager()