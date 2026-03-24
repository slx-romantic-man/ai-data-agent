"""
Row-level permission filter.
Injects row-level filters into SQL queries.
"""
from typing import Dict, Any, List, Optional
import re
from app.models.permission import PermissionContext


class RowFilter:
    """
    Row-level data filter.
    Injects WHERE conditions into SQL queries based on user permissions.
    """

    def __init__(self):
        # Filter column mappings for common patterns
        self._filter_columns = {
            "department": ["department", "dept", "dept_name", "department_id"],
            "business_line": ["business_line", "business", "biz_line", "business_id"],
            "city": ["city", "city_name", "city_id"],
            "region": ["region", "region_name", "region_id"],
            "user_id": ["user_id", "user_uuid", "creator_id", "created_by"],
        }

    def inject_row_filters(
        self,
        sql: str,
        permission: PermissionContext,
        table_alias: Optional[str] = None,
    ) -> str:
        """
        Inject row-level filters into SQL query.

        Args:
            sql: Original SQL query
            permission: Permission context with row filters
            table_alias: Optional table alias for multi-table queries

        Returns:
            Modified SQL with row filters injected
        """
        if not permission.row_filters:
            return sql

        # Parse the SQL to find WHERE clause position
        sql_upper = sql.upper()

        # Generate filter conditions
        conditions = self._generate_filter_conditions(permission.row_filters, table_alias)
        if not conditions:
            return sql

        filter_clause = " AND ".join(conditions)

        # Check if WHERE clause exists
        where_match = re.search(r'\bWHERE\b', sql_upper, re.IGNORECASE)

        if where_match:
            # Insert after WHERE
            insert_pos = where_match.end()
            sql = sql[:insert_pos] + f" ({filter_clause}) AND" + sql[insert_pos:]
        else:
            # Find position before ORDER BY, GROUP BY, LIMIT, etc.
            pattern = r'\b(ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT|OFFSET)\b'
            match = re.search(pattern, sql_upper, re.IGNORECASE)

            if match:
                insert_pos = match.start()
                sql = sql[:insert_pos] + f" WHERE {filter_clause} " + sql[insert_pos:]
            else:
                # Append at the end
                sql = f"{sql.rstrip(';')} WHERE {filter_clause}"

        return sql

    def _generate_filter_conditions(
        self,
        filters: Dict[str, Any],
        table_alias: Optional[str] = None,
    ) -> List[str]:
        """Generate SQL conditions from filter dict."""
        conditions = []

        for key, value in filters.items():
            if value is None:
                continue

            # Find matching column name
            column_names = self._filter_columns.get(key, [key])
            column = column_names[0]  # Use first matching column

            if table_alias:
                column = f"{table_alias}.{column}"

            # Generate condition based on value type
            if isinstance(value, list):
                if len(value) == 1:
                    conditions.append(f"{column} = '{value[0]}'")
                else:
                    values_str = ", ".join(f"'{v}'" for v in value)
                    conditions.append(f"{column} IN ({values_str})")
            elif isinstance(value, str):
                conditions.append(f"{column} = '{value}'")
            elif isinstance(value, (int, float)):
                conditions.append(f"{column} = {value}")
            else:
                conditions.append(f"{column} = '{value}'")

        return conditions

    def apply_time_filter(
        self,
        sql: str,
        time_column: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> str:
        """Apply time range filter to SQL query."""
        conditions = []

        if start_time:
            conditions.append(f"{time_column} >= '{start_time}'")
        if end_time:
            conditions.append(f"{time_column} <= '{end_time}'")

        if not conditions:
            return sql

        time_filter = " AND ".join(conditions)

        # Use the same injection logic
        sql_upper = sql.upper()
        where_match = re.search(r'\bWHERE\b', sql_upper, re.IGNORECASE)

        if where_match:
            insert_pos = where_match.end()
            sql = sql[:insert_pos] + f" ({time_filter}) AND" + sql[insert_pos:]
        else:
            sql = f"{sql.rstrip(';')} WHERE {time_filter}"

        return sql

    def set_filter_columns(self, key: str, columns: List[str]):
        """Set custom filter column mappings."""
        self._filter_columns[key] = columns

    def get_filter_columns(self, key: str) -> List[str]:
        """Get filter column mappings for a key."""
        return self._filter_columns.get(key, [key])


# Global row filter instance
_row_filter: Optional[RowFilter] = None


def get_row_filter() -> RowFilter:
    """Get row filter instance."""
    global _row_filter
    if _row_filter is None:
        _row_filter = RowFilter()
    return _row_filter