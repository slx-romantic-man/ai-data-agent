"""
API Permission Service - Business logic for API permission management.
"""
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.access.database.connection import get_db, DatabaseConnection
from app.access.database.models import (
    APICategory, APIConfig, UserAPIPermission, APICallLog, UserAccount
)
from app.models.api_permission import (
    CategoryCreate, CategoryUpdate, CategoryResponse, CategoryTreeNode,
    APIConfigCreate, APIConfigUpdate, APIConfigPublic, APIConfigAdmin,
    PermissionGrant, PermissionRevoke, UserPermissionResponse,
    APIGrantedUserResponse, PermissionOverview, UserPermissionSummary,
    APIPermissionSummary, APICallLogResponse
)
from app.utils.crypto_utils import encrypt_auth_config, decrypt_auth_config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class APIPermissionService:
    """Service for managing API permissions."""

    def __init__(self, db: Optional[DatabaseConnection] = None):
        self._db = db

    async def _ensure_db(self) -> DatabaseConnection:
        """Ensure database connection is initialized."""
        if self._db is None:
            self._db = await get_db()
        return self._db

    # ==================== Category Management ====================

    async def get_category_tree(self) -> List[CategoryTreeNode]:
        """
        Get all categories as a tree structure.

        Returns:
            List of root categories with children populated.
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            # Get all categories
            result = await session.execute(
                select(APICategory).order_by(APICategory.sort_order, APICategory.name)
            )
            categories = result.scalars().all()

            # Get API counts for each category
            api_counts = {}
            for cat in categories:
                count_result = await session.execute(
                    select(func.count(APIConfig.id)).where(
                        APIConfig.category_id == cat.id
                    )
                )
                api_counts[cat.id] = count_result.scalar() or 0

            # Build tree
            cat_map = {cat.id: self._category_to_tree(cat, api_counts) for cat in categories}
            roots = []

            for cat in categories:
                node = cat_map[cat.id]
                if cat.parent_id and cat.parent_id in cat_map:
                    cat_map[cat.parent_id].children.append(node)
                else:
                    roots.append(node)

            return roots

    def _category_to_tree(self, cat: APICategory, api_counts: Dict[int, int]) -> CategoryTreeNode:
        """Convert category ORM to tree node."""
        return CategoryTreeNode(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            parent_id=cat.parent_id,
            sort_order=cat.sort_order,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
            children=[],
            api_count=api_counts.get(cat.id, 0)
        )

    async def create_category(
        self, name: str, description: Optional[str] = None,
        parent_id: Optional[int] = None, created_by: Optional[int] = None
    ) -> CategoryResponse:
        """Create a new API category."""
        db = await self._ensure_db()
        async with db.get_session() as session:
            category = APICategory(
                name=name,
                description=description,
                parent_id=parent_id,
                created_by=created_by
            )
            session.add(category)
            await session.commit()
            await session.refresh(category)
            return CategoryResponse.model_validate(category)

    async def update_category(
        self, category_id: int, **kwargs
    ) -> Optional[CategoryResponse]:
        """Update an API category."""
        db = await self._ensure_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(APICategory).where(APICategory.id == category_id)
            )
            category = result.scalar_one_or_none()
            if not category:
                return None

            for key, value in kwargs.items():
                if hasattr(category, key) and value is not None:
                    setattr(category, key, value)

            await session.commit()
            await session.refresh(category)
            return CategoryResponse.model_validate(category)

    async def delete_category(self, category_id: int) -> bool:
        """
        Delete a category.
        Fails if category has APIs or children.
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            # Check for APIs in this category
            api_count = await session.execute(
                select(func.count(APIConfig.id)).where(
                    APIConfig.category_id == category_id
                )
            )
            if api_count.scalar() > 0:
                raise ValueError("无法删除：该分类下存在 API")

            # Check for children
            child_count = await session.execute(
                select(func.count(APICategory.id)).where(
                    APICategory.parent_id == category_id
                )
            )
            if child_count.scalar() > 0:
                raise ValueError("无法删除：该分类下存在子分类")

            # Delete
            result = await session.execute(
                select(APICategory).where(APICategory.id == category_id)
            )
            category = result.scalar_one_or_none()
            if category:
                await session.delete(category)
                await session.commit()
                return True
            return False

    # ==================== API Management ====================

    async def create_api(
        self, admin_id: int, data: APIConfigCreate
    ) -> APIConfigAdmin:
        """
        Create a new API configuration.
        Encrypts auth_config before storage.
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            # Check if config_id already exists
            existing = await session.execute(
                select(APIConfig).where(APIConfig.config_id == data.config_id)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"API config_id '{data.config_id}' 已存在")

            # Encrypt auth config
            auth_config_encrypted = None
            if data.auth:
                auth_dict = data.auth.model_dump()
                # Don't encrypt if no actual auth values
                if any([auth_dict.get("api_key_value"), auth_dict.get("bearer_token"),
                        auth_dict.get("password")]):
                    auth_config_encrypted = encrypt_auth_config(auth_dict)

            api = APIConfig(
                config_id=data.config_id,
                name=data.name,
                description=data.description,
                base_url=data.base_url,
                category_id=data.category_id,
                auth_type=data.auth.type.value if data.auth else "none",
                auth_config=auth_config_encrypted,
                endpoints={k: v.model_dump() for k, v in data.endpoints.items()} if data.endpoints else {},
                timeout=data.timeout,
                retry_count=data.retry_count,
                is_active=data.is_active,
                recommended_questions=data.recommended_questions,
                created_by=admin_id
            )
            session.add(api)
            try:
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                if "api_configs.config_id" in str(e):
                    raise ValueError(f"API config_id '{data.config_id}' 已存在") from e
                raise
            await session.refresh(api)

            # Generate embedding in background
            try:
                from app.services.api_retrieval_service import get_api_retrieval_service
                retrieval_service = get_api_retrieval_service()
                import asyncio
                asyncio.create_task(retrieval_service.build_index_for_api(api.id))
            except Exception as e:
                logger.error(f"Failed to trigger embedding generation: {e}")

            return await self._api_to_admin_response(session, api)

    async def update_api(
        self, api_id: int, data: APIConfigUpdate
    ) -> Optional[APIConfigAdmin]:
        """
        Update an API configuration.
        Re-encrypts auth_config if provided.
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(APIConfig).where(APIConfig.id == api_id)
            )
            api = result.scalar_one_or_none()
            if not api:
                return None

            # Update basic fields
            if data.name is not None:
                api.name = data.name
            if data.description is not None:
                api.description = data.description
            if data.base_url is not None:
                api.base_url = data.base_url
            if data.category_id is not None:
                api.category_id = data.category_id
            if data.timeout is not None:
                api.timeout = data.timeout
            if data.retry_count is not None:
                api.retry_count = data.retry_count
            if data.is_active is not None:
                api.is_active = data.is_active

            # Update endpoints
            if data.endpoints is not None:
                api.endpoints = {k: v.model_dump() for k, v in data.endpoints.items()}

            # Update auth config
            if data.auth is not None:
                auth_dict = data.auth.model_dump()
                api.auth_type = auth_dict.get("type", "none")
                if any([auth_dict.get("api_key_value"), auth_dict.get("bearer_token"),
                        auth_dict.get("password")]):
                    api.auth_config = encrypt_auth_config(auth_dict)
                else:
                    api.auth_config = None

            # Update recommended questions
            if data.recommended_questions is not None:
                api.recommended_questions = data.recommended_questions

            await session.commit()
            await session.refresh(api)

            # Generate embedding in background
            try:
                from app.services.api_retrieval_service import get_api_retrieval_service
                retrieval_service = get_api_retrieval_service()
                import asyncio
                asyncio.create_task(retrieval_service.build_index_for_api(api.id))
            except Exception as e:
                logger.error(f"Failed to trigger embedding generation: {e}")

            return await self._api_to_admin_response(session, api)

    async def delete_api(self, api_id: int) -> bool:
        """
        Delete an API configuration.
        Also deletes all user permissions for this API.
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(APIConfig).where(APIConfig.id == api_id)
            )
            api = result.scalar_one_or_none()
            if not api:
                return False

            # Delete associated permissions
            await session.execute(
                select(UserAPIPermission).where(UserAPIPermission.api_config_id == api_id)
            )
            perms = (await session.execute(
                select(UserAPIPermission).where(UserAPIPermission.api_config_id == api_id)
            )).scalars().all()
            for perm in perms:
                await session.delete(perm)

            # Delete API
            await session.delete(api)
            await session.commit()

            # Delete embedding
            try:
                from app.services.vector_store import get_vector_store
                get_vector_store().delete(api_id)
            except Exception as e:
                logger.error(f"Failed to delete embedding: {e}")

            return True

    async def get_all_apis(
        self, category_id: Optional[int] = None, include_auth: bool = False
    ) -> List[APIConfigAdmin]:
        """
        Get all API configurations.

        Args:
            category_id: Filter by category
            include_auth: If True, include decrypted auth_config (admin only)
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            query = select(APIConfig).order_by(APIConfig.name)
            if category_id:
                query = query.where(APIConfig.category_id == category_id)

            result = await session.execute(query)
            apis = result.scalars().all()

            if include_auth:
                return [await self._api_to_admin_response(session, api, decrypt=True) for api in apis]
            else:
                return [await self._api_to_admin_response(session, api, decrypt=False) for api in apis]

    async def get_api_by_id(self, api_id: int) -> Optional[APIConfigAdmin]:
        """Get a single API by ID."""
        db = await self._ensure_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(APIConfig).where(APIConfig.id == api_id)
            )
            api = result.scalar_one_or_none()
            if api:
                return await self._api_to_admin_response(session, api, decrypt=False)
            return None

    async def _api_to_admin_response(
        self, session: AsyncSession, api: APIConfig, decrypt: bool = False
    ) -> APIConfigAdmin:
        """Convert API ORM to admin response model."""
        # Get category path
        category_path = None
        if api.category_id:
            cat_result = await session.execute(
                select(APICategory).where(APICategory.id == api.category_id)
            )
            cat = cat_result.scalar_one_or_none()
            if cat:
                category_path = cat.get_path()

        # Decrypt and mask auth config
        auth_config_masked = None
        if api.auth_config and decrypt:
            try:
                decrypted = decrypt_auth_config(api.auth_config)
                # Mask sensitive values
                auth_config_masked = self._mask_auth_config(decrypted)
            except Exception:
                auth_config_masked = {"error": "Failed to decrypt"}
        elif api.auth_config:
            auth_config_masked = {"masked": True}

        return APIConfigAdmin(
            id=api.id,
            config_id=api.config_id,
            name=api.name,
            description=api.description,
            base_url=api.base_url,
            category_id=api.category_id,
            category_path=category_path,
            auth_type=api.auth_type,
            auth_config=auth_config_masked,
            endpoints=json.loads(api.endpoints) if isinstance(api.endpoints, str) else (api.endpoints or {}),
            timeout=api.timeout,
            retry_count=api.retry_count,
            is_system=api.is_system,
            is_active=api.is_active,
            recommended_questions=api.recommended_questions,
            created_at=api.created_at,
            updated_at=api.updated_at
        )

    def _mask_auth_config(self, auth: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive values in auth config for display."""
        masked = auth.copy()
        sensitive_keys = ["api_key_value", "bearer_token", "password"]
        for key in sensitive_keys:
            if key in masked and masked[key]:
                value = str(masked[key])
                if len(value) > 4:
                    masked[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                else:
                    masked[key] = "****"
        return masked

    # ==================== Permission Management ====================

    async def grant_permissions(
        self, admin_id: int, user_id: str, api_config_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Grant API permissions to a user.
        Skips existing active permissions, reactivates disabled ones.
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            granted = []
            skipped = []
            reactivated = []

            for api_id in api_config_ids:
                # Check if API exists
                api_result = await session.execute(
                    select(APIConfig).where(APIConfig.id == api_id)
                )
                if not api_result.scalar_one_or_none():
                    skipped.append({"api_id": api_id, "reason": "API 不存在"})
                    continue

                # Check existing permission
                perm_result = await session.execute(
                    select(UserAPIPermission).where(
                        and_(
                            UserAPIPermission.user_id == user_id,
                            UserAPIPermission.api_config_id == api_id
                        )
                    )
                )
                existing = perm_result.scalar_one_or_none()

                if existing:
                    if existing.status == "active":
                        skipped.append({"api_id": api_id, "reason": "权限已存在"})
                    else:
                        # Reactivate any non-active status (disabled/revoked/etc.)
                        existing.status = "active"
                        existing.disabled_by = None
                        existing.disabled_at = None
                        existing.disabled_reason = None
                        existing.activated_at = datetime.now()
                        reactivated.append(api_id)
                else:
                    # Create new permission
                    perm = UserAPIPermission(
                        user_id=user_id,
                        api_config_id=api_id,
                        source="admin",
                        status="active",
                        granted_by=admin_id,
                        granted_at=datetime.now(),
                        activated_at=datetime.now()
                    )
                    session.add(perm)
                    granted.append(api_id)

            await session.commit()
            return {
                "granted": granted,
                "reactivated": reactivated,
                "skipped": skipped
            }

    async def revoke_permissions(
        self, admin_id: int, user_id: str, api_config_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Revoke API permissions from a user.
        Soft delete (sets status to disabled).
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            revoked = []
            not_found = []

            for api_id in api_config_ids:
                perm_result = await session.execute(
                    select(UserAPIPermission).where(
                        and_(
                            UserAPIPermission.user_id == user_id,
                            UserAPIPermission.api_config_id == api_id,
                            UserAPIPermission.status == "active"
                        )
                    )
                )
                perm = perm_result.scalar_one_or_none()

                if perm:
                    perm.status = "disabled"
                    perm.disabled_by = admin_id
                    perm.disabled_at = datetime.now()
                    perm.disabled_reason = "管理员撤销"
                    revoked.append(api_id)
                else:
                    not_found.append(api_id)

            await session.commit()
            return {
                "revoked": revoked,
                "not_found": not_found
            }

    async def get_user_permissions(
        self, user_id: str
    ) -> List[UserPermissionResponse]:
        """Get all permissions for a user (admin view)."""
        db = await self._ensure_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(UserAPIPermission, APIConfig)
                .join(APIConfig, UserAPIPermission.api_config_id == APIConfig.id)
                .where(UserAPIPermission.user_id == user_id)
                .order_by(UserAPIPermission.granted_at.desc())
            )
            rows = result.all()

            permissions = []
            for perm, api in rows:
                permissions.append(UserPermissionResponse(
                    id=perm.id,
                    user_id=perm.user_id,
                    api_config_id=perm.api_config_id,
                    api_name=api.name,
                    api_description=api.description,
                    status=perm.status,
                    granted_at=perm.granted_at,
                    granted_by=perm.granted_by
                ))
            return permissions

    async def get_api_granted_users(
        self, api_config_id: int
    ) -> List[APIGrantedUserResponse]:
        """Get all users who have access to an API."""
        db = await self._ensure_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(UserAPIPermission, UserAccount)
                .join(UserAccount, UserAPIPermission.user_id == UserAccount.user_id)
                .where(UserAPIPermission.api_config_id == api_config_id)
                .order_by(UserAPIPermission.granted_at.desc())
            )
            rows = result.all()

            users = []
            for perm, user in rows:
                users.append(APIGrantedUserResponse(
                    user_id=user.user_id,
                    username=user.username,
                    status=perm.status,
                    granted_at=perm.granted_at,
                    department=user.department
                ))
            return users

    # ==================== User Queries (Read-only) ====================

    async def get_my_apis(self, user_id: str) -> List[APIConfigPublic]:
        """
        Get APIs accessible by a user.
        IMPORTANT: Returns APIConfigPublic which does NOT include auth_config!
        Admin users have access to all active APIs.
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            # Check if user is admin
            user_result = await session.execute(
                select(UserAccount).where(UserAccount.user_id == user_id)
            )
            user = user_result.scalar_one_or_none()
            is_admin = user and user.role == "admin"

            if is_admin:
                # Admin: return all active APIs
                result = await session.execute(
                    select(APIConfig).where(APIConfig.is_active == True).order_by(APIConfig.name)
                )
                api_objects = result.scalars().all()
            else:
                # Non-admin: only return APIs with active permission
                result = await session.execute(
                    select(APIConfig, UserAPIPermission)
                    .join(UserAPIPermission, APIConfig.id == UserAPIPermission.api_config_id)
                    .where(
                        and_(
                            UserAPIPermission.user_id == user_id,
                            UserAPIPermission.status == "active",
                            APIConfig.is_active == True
                        )
                    )
                    .order_by(APIConfig.name)
                )
                # Extract just the APIConfig objects from the (APIConfig, UserAPIPermission) tuples
                api_objects = [row[0] for row in result.all()]

            apis = []
            for api in api_objects:
                # Get category path
                category_path = None
                if api.category_id:
                    cat_result = await session.execute(
                        select(APICategory).where(APICategory.id == api.category_id)
                    )
                    cat = cat_result.scalar_one_or_none()
                    if cat:
                        category_path = cat.get_path()

                # IMPORTANT: Using APIConfigPublic which excludes auth_config
                apis.append(APIConfigPublic(
                    id=api.id,
                    config_id=api.config_id,
                    name=api.name,
                    description=api.description,
                    base_url=api.base_url,
                    category_id=api.category_id,
                    category_path=category_path,
                    is_active=api.is_active,
                    endpoints=json.loads(api.endpoints) if isinstance(api.endpoints, str) else (api.endpoints or {}),
                    timeout=api.timeout
                ))
            return apis

    # ==================== Agent Internal Use ====================

    async def get_active_permission(
        self, user_id: str, api_config_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Check if user has active permission for an API.

        Admin users have access to all active APIs.
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            # Check if user is admin
            user_result = await session.execute(
                select(UserAccount).where(UserAccount.user_id == user_id)
            )
            user = user_result.scalar_one_or_none()

            if user and user.role == "admin":
                # Admin has access to all active APIs
                api_result = await session.execute(
                    select(APIConfig).where(
                        and_(
                            APIConfig.id == api_config_id,
                            APIConfig.is_active == True
                        )
                    )
                )
                api = api_result.scalar_one_or_none()
                if api:
                    return {
                        "id": 0,  # Virtual permission for admin
                        "user_id": user_id,
                        "api_config_id": api_config_id,
                        "status": "active"
                    }
                return None

            # Regular user: check explicit permission
            result = await session.execute(
                select(UserAPIPermission).where(
                    and_(
                        UserAPIPermission.user_id == user_id,
                        UserAPIPermission.api_config_id == api_config_id,
                        UserAPIPermission.status == "active"
                    )
                )
            )
            perm = result.scalar_one_or_none()
            if perm:
                return {
                    "id": perm.id,
                    "user_id": perm.user_id,
                    "api_config_id": perm.api_config_id,
                    "status": perm.status
                }
            return None

    async def get_active_api_ids(self, user_id: str) -> List[int]:
        """
        Get list of API IDs the user has access to.

        Admin users have access to all active APIs.
        Regular users only have access to explicitly granted APIs.
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            # Check if user is admin
            user_result = await session.execute(
                select(UserAccount).where(UserAccount.user_id == user_id)
            )
            user = user_result.scalar_one_or_none()

            if user and user.role == "admin":
                # Admin has access to all active APIs
                result = await session.execute(
                    select(APIConfig.id).where(APIConfig.is_active == True)
                )
                return [row[0] for row in result.all()]

            # Regular user: check explicit permissions
            result = await session.execute(
                select(UserAPIPermission.api_config_id).where(
                    and_(
                        UserAPIPermission.user_id == user_id,
                        UserAPIPermission.status == "active"
                    )
                )
            )
            return [row[0] for row in result.all()]

    async def get_api_with_auth(
        self, api_config_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get API configuration with decrypted auth_config.
        FOR INTERNAL USE ONLY - Never expose to API endpoints.
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(APIConfig).where(APIConfig.id == api_config_id)
            )
            api = result.scalar_one_or_none()
            if not api:
                return None

            # Decrypt auth config (or use as-is if not encrypted)
            auth_config = api.auth_config
            if api.auth_config:
                if isinstance(api.auth_config, str):
                    # Encrypted string - decrypt it
                    try:
                        auth_config = decrypt_auth_config(api.auth_config)
                    except Exception as e:
                        logger.error(f"Failed to decrypt auth config: {e}")
                elif isinstance(api.auth_config, dict):
                    # Already a plain dict - use as-is
                    auth_config = api.auth_config

            return {
                "id": api.id,
                "config_id": api.config_id,
                "name": api.name,
                "description": api.description,
                "base_url": api.base_url,
                "auth_type": api.auth_type,
                "auth_config": auth_config,
                "endpoints": json.loads(api.endpoints) if isinstance(api.endpoints, str) else (api.endpoints or {}),
                "timeout": api.timeout,
                "retry_count": api.retry_count,
                "is_active": api.is_active
            }

    # ==================== Logging ====================

    async def log_api_call(
        self, user_id: str, api_config_id: int,
        conversation_id: Optional[str] = None,
        status: str = "success",
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> int:
        """Log an API call."""
        db = await self._ensure_db()
        async with db.get_session() as session:
            log = APICallLog(
                user_id=user_id,
                api_config_id=api_config_id,
                conversation_id=conversation_id,
                status=status,
                response_time_ms=response_time_ms,
                error_message=error_message
            )
            session.add(log)
            await session.commit()
            return log.id

    # ==================== Batch Operations ====================

    async def batch_grant_permissions(
        self, admin_id: int, api_ids: List[int], user_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Batch grant permissions: multiple APIs to multiple users.

        Args:
            admin_id: Admin user ID performing the operation
            api_ids: List of API config IDs to grant
            user_ids: List of user IDs to grant to

        Returns:
            Dict with success/failure counts and details
        """
        db = await self._ensure_db()
        success_count = 0
        failure_count = 0
        details = []

        async with db.get_session() as session:
            for user_id in user_ids:
                for api_id in api_ids:
                    try:
                        # Check if permission already exists
                        result = await session.execute(
                            select(UserAPIPermission).where(
                                and_(
                                    UserAPIPermission.user_id == user_id,
                                    UserAPIPermission.api_config_id == api_id
                                )
                            )
                        )
                        existing = result.scalar_one_or_none()

                        if existing:
                            if existing.status != 'active':
                                existing.status = 'active'
                                existing.granted_at = datetime.utcnow()
                                existing.granted_by = admin_id
                                success_count += 1
                                details.append({
                                    "user_id": user_id,
                                    "api_id": api_id,
                                    "action": "reactivated"
                                })
                            else:
                                details.append({
                                    "user_id": user_id,
                                    "api_id": api_id,
                                    "action": "already_exists"
                                })
                        else:
                            # Create new permission
                            permission = UserAPIPermission(
                                user_id=user_id,
                                api_config_id=api_id,
                                status='active',
                                granted_by=admin_id,
                                granted_at=datetime.utcnow()
                            )
                            session.add(permission)
                            success_count += 1
                            details.append({
                                "user_id": user_id,
                                "api_id": api_id,
                                "action": "granted"
                            })
                    except Exception as e:
                        failure_count += 1
                        details.append({
                            "user_id": user_id,
                            "api_id": api_id,
                            "action": "failed",
                            "error": str(e)
                        })
                        logger.error(f"Failed to grant permission: user={user_id}, api={api_id}, error={e}")

            await session.commit()

        return {
            "success": success_count,
            "failure": failure_count,
            "total": len(user_ids) * len(api_ids),
            "details": details
        }

    async def batch_revoke_permissions(
        self, admin_id: int, permission_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Batch revoke permissions by permission IDs.

        Args:
            admin_id: Admin user ID performing the operation
            permission_ids: List of permission IDs to revoke

        Returns:
            Dict with success/failure counts
        """
        db = await self._ensure_db()
        success_count = 0
        failure_count = 0

        async with db.get_session() as session:
            for perm_id in permission_ids:
                try:
                    result = await session.execute(
                        select(UserAPIPermission).where(UserAPIPermission.id == perm_id)
                    )
                    permission = result.scalar_one_or_none()

                    if permission:
                        permission.status = 'revoked'
                        permission.revoked_at = datetime.utcnow()
                        permission.revoked_by = admin_id
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    failure_count += 1
                    logger.error(f"Failed to revoke permission {perm_id}: {e}")

            await session.commit()

        return {
            "success": success_count,
            "failure": failure_count,
            "total": len(permission_ids)
        }

    async def search_users(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search users by username or user_id (fuzzy match).

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of user dicts with id, user_id, username, role
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(UserAccount).where(
                    or_(
                        UserAccount.user_id.ilike(f"%{query}%"),
                        UserAccount.username.ilike(f"%{query}%")
                    )
                ).limit(limit)
            )
            users = result.scalars().all()

            return [
                {
                    "id": user.id,
                    "user_id": user.user_id,
                    "username": user.username,
                    "role": user.role
                }
                for user in users
            ]

    async def get_uncategorized_apis(self) -> List[Dict[str, Any]]:
        """
        Get all APIs that are not assigned to any category (category_id=NULL).

        Returns:
            List of uncategorized API dicts
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(APIConfig).where(APIConfig.category_id.is_(None))
            )
            apis = result.scalars().all()

            return [
                {
                    "id": api.id,
                    "config_id": api.config_id,
                    "name": api.name,
                    "description": api.description,
                    "base_url": api.base_url,
                    "auth_type": api.auth_type,
                    "is_active": api.is_active,
                    "created_at": api.created_at.isoformat() if api.created_at else None
                }
                for api in apis
            ]

    async def batch_categorize_apis(
        self, api_ids: List[int], category_id: Optional[int]
    ) -> Dict[str, Any]:
        """
        Batch assign APIs to a category (or set to NULL for uncategorized).

        Args:
            api_ids: List of API config IDs to categorize
            category_id: Target category ID (None to uncategorize)

        Returns:
            Dict with success/failure counts
        """
        db = await self._ensure_db()
        success_count = 0
        failure_count = 0

        async with db.get_session() as session:
            # Validate category exists if provided
            if category_id is not None:
                cat_result = await session.execute(
                    select(APICategory).where(APICategory.id == category_id)
                )
                if not cat_result.scalar_one_or_none():
                    return {
                        "success": 0,
                        "failure": len(api_ids),
                        "total": len(api_ids),
                        "error": f"Category {category_id} not found"
                    }

            for api_id in api_ids:
                try:
                    result = await session.execute(
                        select(APIConfig).where(APIConfig.id == api_id)
                    )
                    api = result.scalar_one_or_none()

                    if api:
                        api.category_id = category_id
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    failure_count += 1
                    logger.error(f"Failed to categorize API {api_id}: {e}")

            await session.commit()

        return {
            "success": success_count,
            "failure": failure_count,
            "total": len(api_ids)
        }

    async def get_user_permission_overview(
        self, user_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed permission overview for a user with category grouping.

        Args:
            user_id: User ID to get overview for

        Returns:
            Dict with user info and grouped permissions
        """
        db = await self._ensure_db()
        async with db.get_session() as session:
            # Get user info
            user_result = await session.execute(
                select(UserAccount).where(UserAccount.user_id == user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                return None

            # Get all active permissions
            result = await session.execute(
                select(UserAPIPermission, APIConfig, APICategory).
                join(APIConfig, UserAPIPermission.api_config_id == APIConfig.id).
                outerjoin(APICategory, APIConfig.category_id == APICategory.id).
                where(
                    and_(
                        UserAPIPermission.user_id == user_id,
                        UserAPIPermission.status == 'active'
                    )
                )
            )
            rows = result.all()

            # Group by category
            categorized = {}
            uncategorized = []

            for perm, api, category in rows:
                api_info = {
                    "permission_id": perm.id,
                    "api_id": api.id,
                    "config_id": api.config_id,
                    "name": api.name,
                    "description": api.description,
                    "granted_at": perm.granted_at.isoformat() if perm.granted_at else None
                }

                if category:
                    category_name = category.get_path()
                    if category_name not in categorized:
                        categorized[category_name] = {
                            "category_id": category.id,
                            "category_name": category_name,
                            "apis": []
                        }
                    categorized[category_name]["apis"].append(api_info)
                else:
                    uncategorized.append(api_info)

            return {
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role,
                "categorized": list(categorized.values()),
                "uncategorized": uncategorized,
                "total_permissions": len(rows)
            }

    # ==================== Overview ====================

    async def get_permissions_overview(self) -> PermissionOverview:
        """Get permission overview for admin dashboard."""
        db = await self._ensure_db()
        async with db.get_session() as session:
            # Total APIs
            total_result = await session.execute(
                select(func.count(APIConfig.id))
            )
            total_apis = total_result.scalar() or 0

            # Active APIs
            active_result = await session.execute(
                select(func.count(APIConfig.id)).where(APIConfig.is_active == True)
            )
            active_apis = active_result.scalar() or 0

            # Users with permissions
            users_result = await session.execute(
                select(func.count(func.distinct(UserAPIPermission.user_id))).where(
                    UserAPIPermission.status == "active"
                )
            )
            total_users = users_result.scalar() or 0

            # By user summary
            by_user_result = await session.execute(
                select(
                    UserAPIPermission.user_id,
                    UserAccount.username,
                    UserAccount.department,
                    func.count(UserAPIPermission.id).label("api_count")
                )
                .join(UserAccount, UserAPIPermission.user_id == UserAccount.user_id)
                .where(UserAPIPermission.status == "active")
                .group_by(UserAPIPermission.user_id, UserAccount.username, UserAccount.department)
                .order_by(func.count(UserAPIPermission.id).desc())
                .limit(20)
            )
            by_user = [
                UserPermissionSummary(
                    user_id=row[0],
                    username=row[1],
                    department=row[2],
                    api_count=row[3]
                ) for row in by_user_result.all()
            ]

            # By API summary
            by_api_result = await session.execute(
                select(
                    APIConfig.id,
                    APIConfig.name,
                    func.count(UserAPIPermission.id).label("user_count")
                )
                .outerjoin(UserAPIPermission, and_(
                    APIConfig.id == UserAPIPermission.api_config_id,
                    UserAPIPermission.status == "active"
                ))
                .where(APIConfig.is_active == True)
                .group_by(APIConfig.id, APIConfig.name)
                .order_by(func.count(UserAPIPermission.id).desc())
                .limit(20)
            )
            by_api = [
                APIPermissionSummary(
                    api_id=row[0],
                    api_name=row[1],
                    user_count=row[2]
                ) for row in by_api_result.all()
            ]

            # Recent calls
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent_result = await session.execute(
                select(APICallLog, APIConfig)
                .outerjoin(APIConfig, APICallLog.api_config_id == APIConfig.id)
                .where(APICallLog.called_at >= seven_days_ago)
                .order_by(APICallLog.called_at.desc())
                .limit(50)
            )
            recent_calls = []
            for log, api in recent_result.all():
                recent_calls.append(APICallLogResponse(
                    id=log.id,
                    user_id=log.user_id,
                    api_config_id=log.api_config_id,
                    api_name=api.name if api else None,
                    conversation_id=log.conversation_id,
                    status=log.status,
                    response_time_ms=log.response_time_ms,
                    error_message=log.error_message,
                    called_at=log.called_at
                ))

            return PermissionOverview(
                total_apis=total_apis,
                active_apis=active_apis,
                total_users_with_permissions=total_users,
                by_user=by_user,
                by_api=by_api,
                recent_calls=recent_calls
            )


# Singleton instance
_service: Optional[APIPermissionService] = None


async def get_api_permission_service() -> APIPermissionService:
    """Get or create API permission service instance."""
    global _service
    if _service is None:
        _service = APIPermissionService()
    return _service