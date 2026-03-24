"""
SQL Query Tool - Executes SQL queries with permission filtering.
"""
from typing import Any, Dict, Optional, List

from app.agent.tools.base_tool import BaseTool
from app.models.permission import PermissionContext
from app.models.tool import ToolResult
from app.access.database import get_mysql_client, MySQLClient
from app.access.permission import get_row_filter, get_column_masker, RowFilter, ColumnMasker


class SQLQueryTool(BaseTool):
    """
    Tool for executing SQL queries with permission enforcement.
    """

    def __init__(
        self,
        db_client: Optional[MySQLClient] = None,
        row_filter: Optional[RowFilter] = None,
        column_masker: Optional[ColumnMasker] = None,
    ):
        self._db = db_client
        self._row_filter = row_filter
        self._column_masker = column_masker

    @property
    def name(self) -> str:
        return "sql_query"

    @property
    def description(self) -> str:
        return "Execute SQL SELECT queries on the database. Only SELECT operations are allowed."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "SQL SELECT query to execute",
                },
                "table_name": {
                    "type": "string",
                    "description": "Target table name (optional, used for permission checks)",
                },
            },
            "required": ["sql"],
        }

    @property
    def db(self) -> MySQLClient:
        if self._db is None:
            raise RuntimeError("Database not initialized")
        return self._db

    @property
    def row_filter(self) -> RowFilter:
        if self._row_filter is None:
            self._row_filter = get_row_filter()
        return self._row_filter

    @property
    def column_masker(self) -> ColumnMasker:
        if self._column_masker is None:
            self._column_masker = get_column_masker()
        return self._column_masker

    async def init(self):
        """Initialize database connection."""
        if self._db is None:
            self._db = await get_mysql_client()

    async def execute(
        self,
        params: Dict[str, Any],
        permission: PermissionContext,
    ) -> ToolResult:
        """
        Execute SQL query with permission filtering.

        Args:
            params: Dict with 'sql' key containing the query
            permission: Permission context for row/column filtering

        Returns:
            ToolResult with query data
        """
        try:
            # Validate params
            self.validate_params(params)

            sql = params.get("sql", "")
            table_name = params.get("table_name", self._extract_table_name(sql))

            # Check table permission
            if table_name and not permission.can_access_table(table_name):
                return self._error(f"Access denied to table: {table_name}")

            # Apply row-level filters
            sql = self.row_filter.inject_row_filters(sql, permission)

            # Remove hidden columns from SQL
            hidden_columns = permission.get_hidden_columns_for_table(table_name) if table_name else []
            if hidden_columns:
                sql = self.column_masker.remove_columns_from_sql(sql, hidden_columns)

            # Execute query
            result = await self.db.execute_safe_query(sql)

            if not result.get("success"):
                return self._error(result.get("error", "Query execution failed"))

            data = result.get("data", [])

            # Apply column masking
            if table_name:
                data = self.column_masker.mask_result(data, permission, table_name)
            else:
                # Apply role-based default masking
                data = self.column_masker.mask_result(data, permission)

            return self._success(
                data={"data": data, "sql": sql, "row_count": len(data)},
                metadata={"table": table_name, "original_row_count": result.get("row_count")},
            )

        except ValueError as e:
            return self._error(f"Invalid SQL: {str(e)}")
        except Exception as e:
            return self._error(f"Query execution failed: {str(e)}")

    def _extract_table_name(self, sql: str) -> Optional[str]:
        """Extract table name from SQL query."""
        import re

        # Match FROM clause
        from_match = re.search(r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        if from_match:
            return from_match.group(1)

        # Match JOIN clause
        join_match = re.search(r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        if join_match:
            return join_match.group(1)

        return None


# Global SQL query tool instance
_sql_query_tool: Optional[SQLQueryTool] = None


async def get_sql_query_tool() -> SQLQueryTool:
    """Get SQL query tool instance."""
    global _sql_query_tool
    if _sql_query_tool is None:
        _sql_query_tool = SQLQueryTool()
        await _sql_query_tool.init()
    return _sql_query_tool