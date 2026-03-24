"""
RBAC (Role-Based Access Control) Manager.
Manages role permissions and data scope configurations.
"""
from typing import Dict, List, Optional
from app.models.permission import (
    Role,
    DataScope,
    RolePermission,
    PermissionContext,
)


class RBACManager:
    """
    Role-Based Access Control Manager.
    Manages roles, permissions, and data scopes.
    """

    def __init__(self):
        # Default role configurations
        self._role_permissions: Dict[str, RolePermission] = {
            Role.EMPLOYEE: RolePermission(
                role=Role.EMPLOYEE,
                data_scope=DataScope.DEPARTMENT,
                permissions=["read"],
            ),
            Role.MANAGER: RolePermission(
                role=Role.MANAGER,
                data_scope=DataScope.BUSINESS_LINE,
                permissions=["read", "export"],
            ),
            Role.EXECUTIVE: RolePermission(
                role=Role.EXECUTIVE,
                data_scope=DataScope.COMPANY,
                permissions=["read", "export", "delete"],
            ),
            Role.ADMIN: RolePermission(
                role=Role.ADMIN,
                data_scope=DataScope.COMPANY,
                permissions=["read", "write", "delete", "export"],
            ),
        }

    def get_role_permission(self, role: str) -> Optional[RolePermission]:
        """Get permission configuration for a role."""
        return self._role_permissions.get(role)

    def set_role_permission(self, role: str, permission: RolePermission):
        """Set permission configuration for a role."""
        self._role_permissions[role] = permission

    def get_data_scope(self, role: str) -> str:
        """Get data scope for a role."""
        permission = self.get_role_permission(role)
        if permission:
            return permission.data_scope
        return DataScope.DEPARTMENT

    def has_permission(self, role: str, permission_type: str) -> bool:
        """Check if a role has a specific permission."""
        permission = self.get_role_permission(role)
        if permission:
            return permission_type in permission.permissions
        return False

    def get_allowed_tables(self, role: str) -> List[str]:
        """Get tables allowed for a role."""
        permission = self.get_role_permission(role)
        if permission:
            return permission.allowed_tables
        return []

    def get_denied_tables(self, role: str) -> List[str]:
        """Get tables denied for a role."""
        permission = self.get_role_permission(role)
        if permission:
            return permission.denied_tables
        return []

    def build_permission_context(
        self,
        user_id: str,
        role: str,
        department: Optional[str] = None,
        business_line: Optional[str] = None,
        row_filters: Optional[Dict] = None,
    ) -> PermissionContext:
        """
        Build full permission context for a user.
        """
        role_permission = self.get_role_permission(role)
        if not role_permission:
            role_permission = self._role_permissions[Role.EMPLOYEE]

        # Build row filters based on data scope
        filters = row_filters or {}
        data_scope = role_permission.data_scope

        if data_scope == DataScope.DEPARTMENT and department:
            filters["department"] = department
        elif data_scope == DataScope.BUSINESS_LINE and business_line:
            filters["business_line"] = business_line
        # COMPANY scope has no filters

        return PermissionContext(
            user_id=user_id,
            role=role,
            data_scope=data_scope,
            row_filters=filters,
            allowed_tables=role_permission.allowed_tables,
            denied_tables=role_permission.denied_tables,
            permissions=role_permission.permissions,
        )

    def validate_access(
        self,
        permission_context: PermissionContext,
        table_name: str,
        action: str = "read",
    ) -> bool:
        """
        Validate if user has access to perform action on table.
        """
        # Check table access
        if not permission_context.can_access_table(table_name):
            return False

        # Check action permission
        if not permission_context.has_permission(action):
            return False

        return True


# Global RBAC manager instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """Get RBAC manager instance."""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager