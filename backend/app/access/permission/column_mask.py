"""
Column-level data masking.
Masks sensitive columns in query results.
"""
from typing import Dict, List, Any, Optional
import re
from app.models.permission import PermissionContext


class ColumnMasker:
    """
    Column-level data masker.
    Masks or hides sensitive columns in query results.
    """

    def __init__(self):
        # Default masking rules
        self._masking_rules = {
            # Phone: show first 3 and last 4 digits
            "phone": self._mask_phone,
            "mobile": self._mask_phone,
            "phone_number": self._mask_phone,

            # ID Card: show first 6 and last 4
            "id_card": self._mask_id_card,
            "idcard": self._mask_id_card,
            "id_number": self._mask_id_card,

            # Email: show first 3 chars and domain
            "email": self._mask_email,

            # Bank card: show last 4 digits
            "bank_card": self._mask_bank_card,
            "bankcard": self._mask_bank_card,

            # Salary: show only range
            "salary": self._mask_salary,

            # Name: show only first character
            "name": self._mask_name,
            "real_name": self._mask_name,
            "username": self._mask_name,
        }

        # Default sensitive columns by role
        self._role_masked_columns = {
            "employee": ["phone", "id_card", "salary", "bank_card", "email"],
            "manager": ["id_card", "bank_card"],
            "executive": ["bank_card"],
            "admin": [],
        }

        self._role_hidden_columns = {
            "employee": ["password", "salt"],
            "manager": ["password", "salt"],
            "executive": ["password", "salt"],
            "admin": [],
        }

    def mask_result(
        self,
        data: List[Dict[str, Any]],
        permission: PermissionContext,
        table_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Mask sensitive columns in query results.

        Args:
            data: Query result rows
            permission: Permission context
            table_name: Optional table name for table-specific rules

        Returns:
            Data with masked sensitive columns
        """
        if not data:
            return data

        # Get columns to mask and hide
        masked_columns = set(permission.masked_columns.get(table_name, []))
        hidden_columns = set(permission.hidden_columns.get(table_name, []))

        # Add role-based default columns
        role = permission.role
        masked_columns.update(self._role_masked_columns.get(role, []))
        hidden_columns.update(self._role_hidden_columns.get(role, []))

        if not masked_columns and not hidden_columns:
            return data

        result = []
        for row in data:
            new_row = {}
            for key, value in row.items():
                key_lower = key.lower()

                # Skip hidden columns
                if key_lower in hidden_columns or key in hidden_columns:
                    continue

                # Mask sensitive columns
                if key_lower in masked_columns or key in masked_columns:
                    new_row[key] = self._mask_value(key_lower, value)
                else:
                    new_row[key] = value

            result.append(new_row)

        return result

    def _mask_value(self, column_name: str, value: Any) -> Any:
        """Mask a single value based on column type."""
        if value is None:
            return None

        # Find matching masking rule
        for pattern, mask_func in self._masking_rules.items():
            if pattern in column_name.lower():
                try:
                    return mask_func(str(value))
                except Exception:
                    return "***"

        # Default masking
        return "***"

    def _mask_phone(self, value: str) -> str:
        """Mask phone number: 138****5678"""
        if len(value) < 7:
            return "***"
        return value[:3] + "****" + value[-4:]

    def _mask_id_card(self, value: str) -> str:
        """Mask ID card: 110***********1234"""
        if len(value) < 10:
            return "***"
        return value[:6] + "********" + value[-4:]

    def _mask_email(self, value: str) -> str:
        """Mask email: abc***@example.com"""
        if "@" not in value:
            return "***"
        parts = value.split("@")
        if len(parts[0]) <= 3:
            return parts[0] + "***@" + parts[1]
        return parts[0][:3] + "***@" + parts[1]

    def _mask_bank_card(self, value: str) -> str:
        """Mask bank card: ************1234"""
        if len(value) < 4:
            return "***"
        return "*" * (len(value) - 4) + value[-4:]

    def _mask_salary(self, value: str) -> str:
        """Mask salary: return range instead of exact value."""
        try:
            salary = float(value)
            if salary < 10000:
                return "<1万"
            elif salary < 20000:
                return "1-2万"
            elif salary < 50000:
                return "2-5万"
            else:
                return ">5万"
        except ValueError:
            return "***"

    def _mask_name(self, value: str) -> str:
        """Mask name: 张*"""
        if not value:
            return "***"
        if len(value) == 1:
            return value[0] + "*"
        return value[0] + "*" * (len(value) - 1)

    def add_masking_rule(self, column_pattern: str, mask_func):
        """Add custom masking rule."""
        self._masking_rules[column_pattern.lower()] = mask_func

    def set_role_masked_columns(self, role: str, columns: List[str]):
        """Set default masked columns for a role."""
        self._role_masked_columns[role] = columns

    def set_role_hidden_columns(self, role: str, columns: List[str]):
        """Set default hidden columns for a role."""
        self._role_hidden_columns[role] = columns

    def remove_columns_from_sql(
        self,
        sql: str,
        columns_to_remove: List[str],
    ) -> str:
        """
        Remove sensitive columns from SQL SELECT clause.
        Replaces them with NULL or removes them entirely.
        """
        if not columns_to_remove:
            return sql

        # Find SELECT clause
        select_match = re.search(r'\bSELECT\b(.*?)\bFROM\b', sql, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return sql

        select_clause = select_match.group(1)
        columns = [c.strip() for c in select_clause.split(",")]

        # Filter out sensitive columns
        filtered_columns = []
        for col in columns:
            col_lower = col.lower()
            should_remove = any(
                sensitive.lower() in col_lower
                for sensitive in columns_to_remove
            )
            if not should_remove:
                filtered_columns.append(col)

        # Reconstruct SQL
        new_select = ", ".join(filtered_columns)
        sql = sql[:select_match.start(1)] + new_select + sql[select_match.end(1):]

        return sql


# Global column masker instance
_column_masker: Optional[ColumnMasker] = None


def get_column_masker() -> ColumnMasker:
    """Get column masker instance."""
    global _column_masker
    if _column_masker is None:
        _column_masker = ColumnMasker()
    return _column_masker