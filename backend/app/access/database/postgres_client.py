"""
PostgreSQL database client with specialized query methods.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from app.access.database.connection import DatabaseConnection, get_db


class PostgreSQLClient:
    """PostgreSQL-specific database client."""

    def __init__(self, db: Optional[DatabaseConnection] = None):
        self._db = db

    @property
    def db(self) -> DatabaseConnection:
        if self._db is None:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self._db

    async def init(self):
        """Initialize database connection."""
        if self._db is None:
            self._db = await get_db()

    async def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema information."""
        sql = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """
        rows = await self.db.fetch_all(sql, {"table_name": table_name})
        return [dict(row._mapping) for row in rows]

    async def get_all_tables(self) -> List[str]:
        """Get all table names in the public schema."""
        sql = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """
        rows = await self.db.fetch_all(sql)
        return [row.table_name for row in rows]

    async def get_table_columns(self, table_name: str) -> List[str]:
        """Get column names for a table."""
        sql = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = :table_name
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """
        rows = await self.db.fetch_all(sql, {"table_name": table_name})
        return [row.column_name for row in rows]

    async def execute_query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts."""
        rows = await self.db.fetch_all(sql, params)
        return [dict(row._mapping) for row in rows]

    async def execute_safe_query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a safe query with validation.
        Only allows SELECT queries for security.
        """
        # Validate SQL is read-only
        sql_upper = sql.strip().upper()
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]

        for keyword in forbidden_keywords:
            if keyword in sql_upper:
                raise ValueError(f"Forbidden SQL keyword detected: {keyword}")

        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            raise ValueError("Only SELECT queries are allowed")

        results = await self.execute_query(sql, params)
        return {
            "success": True,
            "data": results,
            "row_count": len(results),
        }

    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            await self.db.fetch_one("SELECT 1")
            return True
        except Exception as e:
            return False


# Global PostgreSQL client instance
_postgres_client: Optional[PostgreSQLClient] = None


async def get_postgres_client() -> PostgreSQLClient:
    """Get PostgreSQL client instance."""
    global _postgres_client
    if _postgres_client is None:
        _postgres_client = PostgreSQLClient()
        await _postgres_client.init()
    return _postgres_client