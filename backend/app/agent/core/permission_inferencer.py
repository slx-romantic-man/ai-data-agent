"""
Permission inferencer module.
Infers and builds permission context for user queries.

DEPRECATED: This module is deprecated.
Permission inference has been moved to the API layer (app/api/dependencies.py).
Use the `get_permission_context` dependency in API endpoints instead.

This module is kept for backward compatibility but should not be used in new code.
All permission context should be built at the API layer and passed to the agent.
"""
import warnings

# Show deprecation warning when module is imported
warnings.warn(
    "PermissionInferencer is deprecated. "
    "Use get_permission_context dependency from app.api.dependencies instead.",
    DeprecationWarning,
    stacklevel=2
)

from typing import Optional, Dict, Any

from app.models.permission import PermissionContext
from app.models.user import UserContext
from app.access.permission import get_rbac_manager, RBACManager


class PermissionInferencer:
    """
    Infers permission context from user context.
    """

    def __init__(self, rbac_manager: Optional[RBACManager] = None):
        self._rbac_manager = rbac_manager

    @property
    def rbac_manager(self) -> RBACManager:
        if self._rbac_manager is None:
            self._rbac_manager = get_rbac_manager()
        return self._rbac_manager

    async def infer(self, user_context: UserContext) -> PermissionContext:
        """
        Infer permission context from user context.

        Args:
            user_context: User context with role, department, etc.

        Returns:
            PermissionContext with full permission details
        """
        return self.rbac_manager.build_permission_context(
            user_id=user_context.user_id,
            role=user_context.role,
            department=user_context.department,
            business_line=user_context.business_line,
            row_filters=user_context.filters,
        )

    async def infer_for_table(
        self,
        user_context: UserContext,
        table_name: str,
    ) -> Dict[str, Any]:
        """
        Infer permission details for a specific table.

        Args:
            user_context: User context
            table_name: Target table name

        Returns:
            Dict with row_filters, masked_columns, hidden_columns
        """
        permission = await self.infer(user_context)

        # Check table access
        if not permission.can_access_table(table_name):
            raise PermissionError(f"User {user_context.user_id} cannot access table {table_name}")

        return {
            "row_filters": permission.row_filters,
            "masked_columns": permission.get_masked_columns_for_table(table_name),
            "hidden_columns": permission.get_hidden_columns_for_table(table_name),
            "can_read": permission.has_permission("read"),
            "can_export": permission.has_permission("export"),
        }

    def get_filter_conditions(
        self,
        permission: PermissionContext,
        table_name: str,
    ) -> Dict[str, Any]:
        """
        Get filter conditions for SQL generation.

        Args:
            permission: Permission context
            table_name: Target table name

        Returns:
            Dict with filter conditions for SQL WHERE clause
        """
        return {
            "row_filters": permission.row_filters,
            "data_scope": permission.data_scope,
        }