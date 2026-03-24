"""
Credit Service - Token-based credit calculation and tracking.
Uses database for storage instead of JSON files.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import math

from sqlalchemy import select, func

from app.access.database.connection import get_db
from app.access.database.models import CreditLog
from app.models.user import CreditTransaction
from app.services.user_service import get_user_service, UserService


# Credit calculation constant
CREDITS_PER_TOKEN = 2000  # 2000 tokens = 1 credit


class CreditService:
    """
    Service for calculating and tracking credit usage.
    Storage: MySQL/PostgreSQL database

    Credit calculation: ceil(total_tokens / 2000)
    """

    def __init__(self):
        self._db = None

    async def _get_db(self):
        """Get database connection."""
        if self._db is None:
            self._db = await get_db()
        return self._db

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

    def _db_log_to_pydantic(self, db_log: CreditLog) -> CreditTransaction:
        """Convert database credit log to Pydantic model."""
        return CreditTransaction(
            timestamp=db_log.created_at,
            user_id=db_log.user_id or "",
            session_id=db_log.session_id,
            query=db_log.query or "",
            input_tokens=db_log.input_tokens or 0,
            output_tokens=db_log.output_tokens or 0,
            total_tokens=db_log.total_tokens or 0,
            credits_deducted=db_log.credits_deducted or 0,
            balance_after=db_log.balance_after or 0
        )

    def calculate_credits(self, input_tokens: int, output_tokens: int) -> int:
        """
        Calculate credits to deduct based on token usage.

        Formula: ceil(total_tokens / 2000)
        Minimum: 1 credit per query
        """
        total = input_tokens + output_tokens
        if total <= 0:
            return 1  # Minimum 1 credit
        return math.ceil(total / CREDITS_PER_TOKEN)

    def check_balance(self, login_id: str) -> bool:
        """Check if user has enough credits for a query."""
        user_service = get_user_service()
        return user_service.check_quota(login_id)

    def deduct_credits(
        self,
        login_id: str,
        input_tokens: int,
        output_tokens: int,
        query: str,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Deduct credits from user's balance and log the transaction.

        Returns:
            Dict with credits_deducted, balance_after, success
        """
        return self._run_async(
            self._deduct_credits_async(login_id, input_tokens, output_tokens, query, session_id)
        )

    async def _deduct_credits_async(
        self,
        login_id: str,
        input_tokens: int,
        output_tokens: int,
        query: str,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Deduct credits from user's balance and log the transaction in database.
        """
        user_service = get_user_service()
        user = user_service.get_user(login_id)

        if not user:
            return {
                "success": False,
                "error": "User not found",
                "credits_deducted": 0,
                "balance_after": 0
            }

        # Admin has unlimited credits
        if user.has_unlimited_credits():
            credits = self.calculate_credits(input_tokens, output_tokens)
            return {
                "success": True,
                "credits_deducted": credits,
                "balance_after": -1,  # Unlimited
                "is_unlimited": True
            }

        # Check and reset quota if new day
        user_service.check_and_reset_if_needed(login_id)

        # Calculate credits
        credits = self.calculate_credits(input_tokens, output_tokens)

        # Check balance
        if user.quota.current_balance < credits:
            return {
                "success": False,
                "error": "Insufficient credits",
                "credits_deducted": 0,
                "balance_after": user.quota.current_balance,
                "required": credits
            }

        # Deduct credits
        success = user_service.deduct_credits(login_id, credits)

        if not success:
            return {
                "success": False,
                "error": "Failed to deduct credits",
                "credits_deducted": 0,
                "balance_after": user.quota.current_balance
            }

        # Log transaction to database
        user = user_service.get_user(login_id)
        balance_after = user.quota.current_balance if user else 0

        db = await self._get_db()
        now = datetime.now()

        async with db.get_session() as session:
            db_log = CreditLog(
                user_id=user.user_id if user else login_id,
                username=user.username if user else login_id,
                query=query[:500],  # Truncate long queries
                session_id=session_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
                credits_deducted=credits,
                balance_after=balance_after,
                created_at=now,
            )
            session.add(db_log)
            await session.commit()

        return {
            "success": True,
            "credits_deducted": credits,
            "balance_after": balance_after,
            "is_unlimited": False
        }

    def get_logs(self, user_id: str = None, limit: int = 100) -> List[CreditTransaction]:
        """Get credit logs, optionally filtered by user."""
        return self._run_async(self._get_logs_async(user_id, limit))

    async def _get_logs_async(self, user_id: str = None, limit: int = 100) -> List[CreditTransaction]:
        """Get credit logs from database."""
        db = await self._get_db()
        async with db.get_session() as session:
            if user_id:
                result = await session.execute(
                    select(CreditLog)
                    .where(CreditLog.user_id == user_id)
                    .order_by(CreditLog.created_at.desc())
                    .limit(limit)
                )
            else:
                result = await session.execute(
                    select(CreditLog)
                    .order_by(CreditLog.created_at.desc())
                    .limit(limit)
                )
            db_logs = result.scalars().all()
            return [self._db_log_to_pydantic(log) for log in db_logs]

    def get_user_usage_stats(self, user_id: str) -> Dict[str, Any]:
        """Get usage statistics for a user."""
        return self._run_async(self._get_user_usage_stats_async(user_id))

    async def _get_user_usage_stats_async(self, user_id: str) -> Dict[str, Any]:
        """Get usage statistics for a user from database."""
        db = await self._get_db()
        async with db.get_session() as session:
            # Get aggregated stats
            result = await session.execute(
                select(
                    func.count(CreditLog.id).label("total_queries"),
                    func.sum(CreditLog.total_tokens).label("total_tokens"),
                    func.sum(CreditLog.credits_deducted).label("total_credits")
                ).where(CreditLog.user_id == user_id)
            )
            row = result.one()

            total_queries = row.total_queries or 0
            total_tokens = row.total_tokens or 0
            total_credits = row.total_credits or 0

            return {
                "total_queries": total_queries,
                "total_tokens": total_tokens,
                "total_credits_used": total_credits,
                "avg_tokens_per_query": total_tokens // total_queries if total_queries > 0 else 0
            }

    def get_all_logs(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all credit logs (admin only)."""
        return self._run_async(self._get_all_logs_async(limit))

    async def _get_all_logs_async(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get all credit logs from database (admin only)."""
        db = await self._get_db()
        async with db.get_session() as session:
            result = await session.execute(
                select(CreditLog)
                .order_by(CreditLog.created_at.desc())
                .limit(limit)
            )
            db_logs = result.scalars().all()

            logs = []
            for log in db_logs:
                logs.append({
                    "id": log.id,
                    "user_id": log.user_id,
                    "username": log.username,
                    "session_id": log.session_id,
                    "query": log.query,
                    "input_tokens": log.input_tokens,
                    "output_tokens": log.output_tokens,
                    "total_tokens": log.total_tokens,
                    "credits_deducted": log.credits_deducted,
                    "balance_after": log.balance_after,
                    "timestamp": log.created_at.isoformat()
                })
            return logs


# Global credit service instance
_credit_service: Optional[CreditService] = None


def get_credit_service() -> CreditService:
    """Get credit service instance."""
    global _credit_service
    if _credit_service is None:
        _credit_service = CreditService()
    return _credit_service