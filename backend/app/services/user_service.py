"""
User Service - User management and quota operations.
Uses database for storage instead of JSON files.
"""
from typing import Optional, List
from datetime import datetime
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.user import (
    UserAccount as UserAccountPydantic,
    UserQuota as UserQuotaPydantic,
    UserContext
)
from app.access.database.connection import get_db, reset_db
import bcrypt
from app.access.database.models import (
    UserAccount as UserAccountDB,
    UserQuota as UserQuotaDB
)


def _hash_if_plain(password: str) -> str:
    """Hash password if it appears to be plaintext (not already bcrypt)."""
    if not password:
        return password
    # bcrypt hashes start with $2b$, $2a$, or $2y$
    if password.startswith(("$2b$", "$2a$", "$2y$")):
        return password
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


class UserService:
    """
    Service for managing user accounts and quotas.
    Storage: MySQL/PostgreSQL database
    """

    def __init__(self):
        self._db = None

    async def _get_db(self):
        """Get database connection."""
        if self._db is None:
            self._db = await get_db()
        return self._db

    async def _get_user_by_login_id_db(self, session: AsyncSession, login_id: str) -> Optional[UserAccountDB]:
        """Get database user model by login_id."""
        result = await session.execute(
            select(UserAccountDB)
            .options(joinedload(UserAccountDB.quota))
            .where(UserAccountDB.login_id == login_id)
        )
        return result.scalar_one_or_none()

    def _db_to_pydantic(self, db_user: UserAccountDB, db_quota: UserQuotaDB = None) -> UserAccountPydantic:
        """Convert database model to Pydantic model."""
        if db_quota is None:
            db_quota = db_user.quota if hasattr(db_user, 'quota') else None

        return UserAccountPydantic(
            user_id=db_user.user_id,
            login_id=db_user.login_id,
            username=db_user.username,
            email=getattr(db_user, 'email', None),
            phone=getattr(db_user, 'phone', None),
            avatar_url=getattr(db_user, 'avatar_url', None),
            password=db_user.password,
            role=db_user.role,
            department=db_user.department,
            business_line=db_user.business_line,
            auth_type=getattr(db_user, 'auth_type', 'local'),
            is_active=getattr(db_user, 'is_active', True),
            quota=UserQuotaPydantic(
                daily_limit=db_quota.daily_limit if db_quota else 100,
                current_balance=db_quota.current_balance if db_quota else 100,
                last_reset=db_quota.last_reset if db_quota else datetime.now()
            ),
            user_apis=[],  # TODO: Load from user_api_configs table
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )

    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're in an async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            # Reset database connection for fresh event loop
            self._db = None
            return asyncio.run(coro)

    def get_user(self, login_id: str) -> Optional[UserAccountPydantic]:
        """Get user by login ID."""
        return self._run_async(self._get_user_async(login_id))

    async def _get_user_async(self, login_id: str) -> Optional[UserAccountPydantic]:
        """Get user by login ID."""
        db = await self._get_db()
        async with db.get_session() as session:
            db_user = await self._get_user_by_login_id_db(session, login_id)
            if not db_user:
                return None
            return self._db_to_pydantic(db_user)

    def get_user_by_user_id(self, user_id: str) -> Optional[UserAccountPydantic]:
        """Get user by user_id field."""
        return self._run_async(self._get_user_by_user_id_async(user_id))

    async def _get_user_by_user_id_async(self, user_id: str) -> Optional[UserAccountPydantic]:
        """Get user by user_id field."""
        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(UserAccountDB)
                .options(joinedload(UserAccountDB.quota))
                .where(UserAccountDB.user_id == user_id)
            )
            db_user = result.scalar_one_or_none()
            if not db_user:
                return None
            return self._db_to_pydantic(db_user)

    def get_user_by_email(self, email: str) -> Optional[UserAccountPydantic]:
        """Get user by email (for CIA login lookup)."""
        return self._run_async(self._get_user_by_email_async(email))

    async def _get_user_by_email_async(self, email: str) -> Optional[UserAccountPydantic]:
        """Get user by email."""
        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(UserAccountDB)
                .options(joinedload(UserAccountDB.quota))
                .where(UserAccountDB.email == email)
            )
            db_user = result.scalar_one_or_none()
            if not db_user:
                return None
            return self._db_to_pydantic(db_user)

    def get_user_context(self, user_id: str) -> Optional[UserContext]:
        """Get UserContext for a user (for request processing)."""
        user = self.get_user_by_user_id(user_id)
        if not user:
            return None
        # Reject disabled/inactive users
        if not user.is_active:
            return None

        return UserContext(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            department=user.department,
            business_line=user.business_line,
            permissions=self._get_permissions(user.role),
            filters=self._get_filters(user)
        )

    def _get_permissions(self, role: str) -> List[str]:
        """Get permissions based on role."""
        if role == "admin":
            return ["read", "write", "delete", "admin", "export"]
        elif role == "manager":
            return ["read", "write", "export"]
        else:
            return ["read", "export"]

    def _get_filters(self, user: UserAccountPydantic) -> dict:
        """Get data filters based on user."""
        filters = {}
        if user.department:
            filters["department"] = user.department
        if user.business_line:
            filters["business_line"] = user.business_line
        return filters

    def list_users(self) -> List[UserAccountPydantic]:
        """List all users."""
        return self._run_async(self._list_users_async())

    async def _list_users_async(self) -> List[UserAccountPydantic]:
        """List all users from database."""
        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(UserAccountDB).options(joinedload(UserAccountDB.quota))
            )
            db_users = result.scalars().all()
            return [self._db_to_pydantic(u) for u in db_users]

    def create_user(self, login_id: str, user_data: dict) -> UserAccountPydantic:
        """Create a new user."""
        return self._run_async(self._create_user_async(login_id, user_data))

    async def _create_user_async(self, login_id: str, user_data: dict) -> UserAccountPydantic:
        """Create a new user in database."""
        db = await self._get_db()
        now = datetime.now()

        async with db.get_session() as session:
            # Check if exists
            existing = await self._get_user_by_login_id_db(session, login_id)
            if existing:
                raise ValueError(f"User {login_id} already exists")

            # Create user
            db_user = UserAccountDB(
                user_id=user_data.get("user_id", login_id),
                login_id=login_id,  # Store login_id
                username=user_data.get("username", login_id),
                email=user_data.get("email"),
                phone=user_data.get("phone"),
                avatar_url=user_data.get("avatar_url"),
                password=_hash_if_plain(user_data.get("password", "")),
                role=user_data.get("role", "employee"),
                department=user_data.get("department"),
                business_line=user_data.get("business_line"),
                auth_type=user_data.get("auth_type", "local"),
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(db_user)
            await session.flush()

            # Create quota
            db_quota = UserQuotaDB(
                user_id=db_user.id,
                daily_limit=user_data.get("daily_limit", 100),
                current_balance=user_data.get("current_balance", 100),
                last_reset=now,
            )
            session.add(db_quota)

            return self._db_to_pydantic(db_user, db_quota)

    def update_user(self, login_id: str, data: dict) -> bool:
        """Update user data."""
        return self._run_async(self._update_user_async(login_id, data))

    async def _update_user_async(self, login_id: str, data: dict) -> bool:
        """Update user data in database."""
        db = await self._get_db()
        async with db.get_session() as session:
            db_user = await self._get_user_by_login_id_db(session, login_id)
            if not db_user:
                return False

            if "username" in data:
                db_user.username = data["username"]
            if "password" in data:
                db_user.password = data["password"]
            if "role" in data:
                db_user.role = data["role"]
            if "department" in data:
                db_user.department = data["department"]
            if "business_line" in data:
                db_user.business_line = data["business_line"]
            if "email" in data:
                db_user.email = data["email"]
            if "phone" in data:
                db_user.phone = data["phone"]
            if "avatar_url" in data:
                db_user.avatar_url = data["avatar_url"]
            if "auth_type" in data:
                db_user.auth_type = data["auth_type"]
            if "is_active" in data:
                db_user.is_active = data["is_active"]

            db_user.updated_at = datetime.now()
            return True

    def set_user_active(self, login_id: str, is_active: bool) -> bool:
        """Enable or disable a user. Cannot disable admin users."""
        return self._run_async(self._set_user_active_async(login_id, is_active))

    async def _set_user_active_async(self, login_id: str, is_active: bool) -> bool:
        """Enable or disable a user in database."""
        db = await self._get_db()
        async with db.get_session() as session:
            db_user = await self._get_user_by_login_id_db(session, login_id)
            if not db_user:
                return False
            # Guard: cannot disable/enable admin users
            if db_user.role == "admin":
                return False
            db_user.is_active = is_active
            db_user.updated_at = datetime.now()
            await session.commit()
            return True

    def delete_user(self, login_id: str) -> bool:
        """Delete a user."""
        return self._run_async(self._delete_user_async(login_id))

    async def _delete_user_async(self, login_id: str) -> bool:
        """Delete a user from database. Cannot delete admin users."""
        db = await self._get_db()
        async with db.get_session() as session:
            db_user = await self._get_user_by_login_id_db(session, login_id)
            if not db_user:
                return False
            # Guard: cannot delete admin users
            if db_user.role == "admin":
                return False

            # Delete associated quota first to avoid orphan records
            if db_user.quota:
                await session.delete(db_user.quota)

            await session.delete(db_user)
            await session.commit()
            return True

    def check_quota(self, login_id: str) -> bool:
        """Check if user has quota available."""
        user = self.get_user(login_id)
        if not user:
            return False

        if user.has_unlimited_credits():
            return True

        return user.quota.current_balance > 0

    def deduct_credits(self, login_id: str, credits: int) -> bool:
        """Deduct credits from user's balance."""
        return self._run_async(self._deduct_credits_async(login_id, credits))

    async def _deduct_credits_async(self, login_id: str, credits: int) -> bool:
        """Deduct credits from user's balance in database."""
        db = await self._get_db()
        async with db.get_session() as session:
            db_user = await self._get_user_by_login_id_db(session, login_id)
            if not db_user:
                return False

            # Admin has unlimited quota
            if db_user.role == "admin" or (db_user.quota and db_user.quota.daily_limit == -1):
                return True

            if not db_user.quota:
                # Missing quota record: auto-create with 0 balance, then check if enough
                from app.access.database.models import UserQuota
                try:
                    now = datetime.now()
                    db_quota = UserQuotaDB(
                        user_id=db_user.id,
                        daily_limit=100,
                        current_balance=0,
                        last_reset=now,
                    )
                    session.add(db_quota)
                    await session.flush()
                    await session.refresh(db_user, ["quota"])
                except Exception:
                    return False

            if db_user.quota.current_balance < credits:
                return False

            db_user.quota.current_balance -= credits
            db_user.updated_at = datetime.now()
            return True

    def add_credits(self, login_id: str, credits: int) -> bool:
        """Add credits to user's balance."""
        return self._run_async(self._add_credits_async(login_id, credits))

    async def _add_credits_async(self, login_id: str, credits: int) -> bool:
        """Add credits to user's balance in database."""
        from sqlalchemy.exc import IntegrityError
        from app.access.database.models import UserQuota

        db = await self._get_db()
        async with db.get_session() as session:
            db_user = await self._get_user_by_login_id_db(session, login_id)
            if not db_user:
                return False

            # Admin has unlimited quota
            if db_user.role == "admin" or (db_user.quota and db_user.quota.daily_limit == -1):
                return True

            if not db_user.quota:
                # Auto-create missing quota record (handle race condition)
                try:
                    now = datetime.now()
                    db_quota = UserQuotaDB(
                        user_id=db_user.id,
                        daily_limit=100,
                        current_balance=0,
                        last_reset=now,
                    )
                    session.add(db_quota)
                    await session.flush()
                    await session.refresh(db_user, ["quota"])
                except IntegrityError:
                    # Another request already created the quota, re-query
                    await session.rollback()
                    db_user = await self._get_user_by_login_id_db(session, login_id)
                    if not db_user or not db_user.quota:
                        return False

            db_user.quota.current_balance += credits
            db_user.updated_at = datetime.now()
            return True

    def adjust_quota(self, login_id: str, amount: int) -> bool:
        """Adjust user's quota (positive to add, negative to deduct)."""
        if amount >= 0:
            return self.add_credits(login_id, amount)
        else:
            return self.deduct_credits(login_id, -amount)

    def reset_daily_quotas(self):
        """Reset all users' daily quotas (called at midnight)."""
        self._run_async(self._reset_daily_quotas_async())

    async def _reset_daily_quotas_async(self):
        """Reset all users' daily quotas in database."""
        db = await self._get_db()
        now = datetime.now()
        async with db.get_session() as session:
            result = await session.execute(select(UserQuotaDB))
            quotas = result.scalars().all()
            for quota in quotas:
                if quota.daily_limit != -1:  # Not unlimited
                    quota.current_balance = quota.daily_limit
                    quota.last_reset = now

    def check_and_reset_if_needed(self, login_id: str):
        """Check if quota needs reset (new day) and reset if needed."""
        self._run_async(self._check_and_reset_if_needed_async(login_id))

    async def _check_and_reset_if_needed_async(self, login_id: str):
        """Check if quota needs reset and reset if needed."""
        db = await self._get_db()
        async with db.get_session() as session:
            db_user = await self._get_user_by_login_id_db(session, login_id)
            if not db_user or not db_user.quota:
                return

            # Admin has unlimited quota
            if db_user.role == "admin" or db_user.quota.daily_limit == -1:
                return

            now = datetime.now()
            last_reset = db_user.quota.last_reset

            # Check if it's a new day
            if now.date() > last_reset.date():
                db_user.quota.current_balance = db_user.quota.daily_limit
                db_user.quota.last_reset = now
                db_user.updated_at = now

    # ==================== User API Management ====================

    def get_user_apis(self, user_id: str) -> List[str]:
        """Get the list of API IDs accessible by the user."""
        # TODO: Implement with user_api_configs table
        return []

    def add_user_api(self, user_id: str, api_id: str) -> bool:
        """Add an API to the user's accessible APIs list."""
        # TODO: Implement with user_api_configs table
        return True

    def remove_user_api(self, user_id: str, api_id: str) -> bool:
        """Remove an API from the user's accessible APIs list."""
        # TODO: Implement with user_api_configs table
        return True

    def get_login_id_by_user_id(self, user_id: str) -> Optional[str]:
        """Get login_id from user_id."""
        return self._run_async(self._get_login_id_by_user_id_async(user_id))

    async def _get_login_id_by_user_id_async(self, user_id: str) -> Optional[str]:
        """Get login_id from user_id from database."""
        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(UserAccountDB.login_id).where(UserAccountDB.user_id == user_id)
            )
            login_id = result.scalar_one_or_none()
            return login_id


# Global user service instance
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """Get user service instance."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service