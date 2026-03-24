"""
Database connection management with async support.
"""
import asyncio
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from app.config.settings import settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class DatabaseConnection:
    """Async database connection manager."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL
        self._engine = None
        self._session_factory = None

    async def init(self):
        """Initialize database connection."""
        # Use NullPool to avoid connection pool issues with multiple event loops
        self._engine = create_async_engine(
            self.database_url,
            poolclass=NullPool,
            echo=settings.DEBUG,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def close(self):
        """Close database connection."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session context manager."""
        if not self._session_factory:
            await self.init()
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def execute_raw(self, sql: str, params: Optional[dict] = None):
        """Execute raw SQL query."""
        async with self.get_session() as session:
            result = await session.execute(text(sql), params or {})
            return result

    async def fetch_all(self, sql: str, params: Optional[dict] = None) -> list:
        """Fetch all rows from query."""
        async with self.get_session() as session:
            result = await session.execute(text(sql), params or {})
            return result.fetchall()

    async def fetch_one(self, sql: str, params: Optional[dict] = None):
        """Fetch one row from query."""
        async with self.get_session() as session:
            result = await session.execute(text(sql), params or {})
            return result.fetchone()


# Global database connection instance
_db_connection: Optional[DatabaseConnection] = None
_current_loop_id = None


async def get_db() -> DatabaseConnection:
    """Get database connection instance."""
    global _db_connection, _current_loop_id

    # Check if event loop changed (happens when asyncio.run() creates new loop)
    try:
        current_loop = asyncio.get_running_loop()
        current_loop_id = id(current_loop)
    except RuntimeError:
        current_loop_id = None

    # Reset connection if loop changed
    if _current_loop_id is not None and _current_loop_id != current_loop_id:
        if _db_connection:
            try:
                await _db_connection.close()
            except Exception:
                pass
            _db_connection = None

    _current_loop_id = current_loop_id

    if _db_connection is None:
        _db_connection = DatabaseConnection()
        await _db_connection.init()
    return _db_connection


async def reset_db():
    """Reset database connection (create fresh connection)."""
    global _db_connection
    if _db_connection:
        try:
            await _db_connection.close()
        except Exception:
            pass
    _db_connection = DatabaseConnection()
    await _db_connection.init()
    return _db_connection


async def close_db():
    """Close database connection."""
    global _db_connection
    if _db_connection:
        await _db_connection.close()
        _db_connection = None


async def get_engine():
    """Get database engine instance."""
    db = await get_db()
    return db._engine


# Create engine for table creation
engine = None


async def get_engine_for_init():
    """Get or create engine for initialization."""
    global engine
    if engine is None:
        from sqlalchemy.ext.asyncio import create_async_engine
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            echo=settings.DEBUG,
        )
    return engine