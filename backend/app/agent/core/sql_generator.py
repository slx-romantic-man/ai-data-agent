"""
SQL Generator module.
Generates safe SQL queries from natural language.
"""
import json
import re
from typing import Optional, Dict, Any, List

from app.config.llm_config import BaseLLMClient, get_llm
from app.models.chat import IntentResult
from app.models.permission import PermissionContext
from app.agent.prompts.sql_prompt import get_sql_prompt, get_sql_validation_prompt


class SQLGenerator:
    """
    Generates SQL queries from natural language queries.
    """

    # Dangerous SQL keywords that should be blocked
    DANGEROUS_KEYWORDS = [
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
        "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE",
        "INTO", "OUTFILE", "LOAD_FILE",
    ]

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self._llm = llm_client
        self._table_schema_cache: Dict[str, str] = {}

    @property
    def llm(self) -> BaseLLMClient:
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    async def generate(
        self,
        user_query: str,
        intent: IntentResult,
        permission: PermissionContext,
        table_schema: str,
    ) -> str:
        """
        Generate SQL query from natural language.

        Args:
            user_query: User's natural language query
            intent: Recognized intent
            permission: Permission context for the user
            table_schema: Database schema information

        Returns:
            Generated SQL query string
        """
        # Build permission filters
        permission_filters = self._build_permission_filters(permission)

        # Generate SQL using LLM
        prompt = get_sql_prompt(
            table_schema=table_schema,
            user_query=user_query,
            intent_result=intent.model_dump(),
            permission_filters=permission_filters,
        )

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个专业的SQL生成器，负责将自然语言转换为安全、准确的SQL查询。"},
            {"role": "user", "content": prompt}
        ])

        # Extract and validate SQL
        sql = self._extract_sql(response)
        sql = self._validate_and_sanitize(sql)

        return sql

    def _build_permission_filters(self, permission: PermissionContext) -> Dict[str, Any]:
        """Build filter conditions from permission context."""
        filters = {}

        # Add row-level filters
        if permission.row_filters:
            filters.update(permission.row_filters)

        return {
            "row_filters": filters,
            "data_scope": permission.data_scope,
        }

    def _extract_sql(self, response: str) -> str:
        """Extract SQL from LLM response."""
        # Try to find SQL in code blocks
        code_block_match = re.search(r'```sql\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
        if code_block_match:
            return code_block_match.group(1).strip()

        code_block_match = re.search(r'```\s*([\s\S]*?)\s*```', response)
        if code_block_match:
            return code_block_match.group(1).strip()

        # Try to find SELECT statement
        select_match = re.search(r'(SELECT\s+[\s\S]+?;?)', response, re.IGNORECASE)
        if select_match:
            return select_match.group(1).strip()

        # Return the whole response if no pattern matched
        return response.strip()

    def _validate_and_sanitize(self, sql: str) -> str:
        """Validate and sanitize SQL query."""
        sql_upper = sql.upper()

        # Check for dangerous keywords
        for keyword in self.DANGEROUS_KEYWORDS:
            # Use word boundary to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                raise ValueError(f"Dangerous SQL keyword detected: {keyword}")

        # Ensure it starts with SELECT or WITH
        if not sql_upper.strip().startswith(("SELECT", "WITH")):
            raise ValueError("Only SELECT queries are allowed")

        # Ensure there's no SQL injection patterns
        injection_patterns = [
            r';.*\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b',  # Multiple statements
            r'UNION\s+SELECT',  # UNION injection
            r'--',  # Comment injection
            r'/\*',  # Block comment injection
            r'@@',  # System variables
            r'CHAR\s*\(',  # CHAR encoding bypass
        ]

        for pattern in injection_patterns:
            if re.search(pattern, sql_upper):
                raise ValueError("Potential SQL injection detected")

        # Add LIMIT if not present
        if "LIMIT" not in sql_upper:
            sql = sql.rstrip(";") + " LIMIT 1000"

        return sql

    def inject_permission_filters(
        self,
        sql: str,
        permission: PermissionContext,
    ) -> str:
        """
        Inject permission filters into SQL query.

        Args:
            sql: Original SQL query
            permission: Permission context with row filters

        Returns:
            SQL with injected filters
        """
        if not permission.row_filters:
            return sql

        # Build WHERE conditions
        conditions = []
        for key, value in permission.row_filters.items():
            if isinstance(value, str):
                conditions.append(f"{key} = '{value}'")
            elif isinstance(value, (int, float)):
                conditions.append(f"{key} = {value}")
            elif isinstance(value, list):
                values_str = ", ".join(f"'{v}'" for v in value)
                conditions.append(f"{key} IN ({values_str})")

        if not conditions:
            return sql

        filter_clause = " AND ".join(conditions)

        # Find WHERE clause position
        where_match = re.search(r'\bWHERE\b', sql, re.IGNORECASE)

        if where_match:
            # Insert after WHERE
            insert_pos = where_match.end()
            sql = sql[:insert_pos] + f" ({filter_clause}) AND" + sql[insert_pos:]
        else:
            # Find position before ORDER BY, GROUP BY, LIMIT
            pattern = r'\b(ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT)\b'
            match = re.search(pattern, sql, re.IGNORECASE)

            if match:
                insert_pos = match.start()
                sql = sql[:insert_pos] + f" WHERE {filter_clause} " + sql[insert_pos:]
            else:
                # Append at the end
                sql = f"{sql.rstrip(';')} WHERE {filter_clause}"

        return sql

    async def validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        Validate SQL query for safety.

        Args:
            sql: SQL query to validate

        Returns:
            Dict with validation result
        """
        try:
            self._validate_and_sanitize(sql)
            return {
                "is_valid": True,
                "sql": sql,
            }
        except ValueError as e:
            return {
                "is_valid": False,
                "error": str(e),
            }

    def set_table_schema(self, table_name: str, schema: str):
        """Cache table schema for reuse."""
        self._table_schema_cache[table_name] = schema

    def get_table_schema(self, table_name: str) -> Optional[str]:
        """Get cached table schema."""
        return self._table_schema_cache.get(table_name)