"""
Permission models for RBAC, row-level, and column-level access control.
"""
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class Role(str, Enum):
    """User roles."""
    EMPLOYEE = "employee"
    MANAGER = "manager"
    EXECUTIVE = "executive"
    ADMIN = "admin"


class DataScope(str, Enum):
    """Data scope levels."""
    DEPARTMENT = "department"
    BUSINESS_LINE = "business_line"
    COMPANY = "company"


class PermissionType(str, Enum):
    """Permission types."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"


class RolePermission(BaseModel):
    """Role-based permission configuration."""
    role: str = Field(..., description="User role")
    data_scope: str = Field(default="department", description="Data access scope")
    allowed_tables: List[str] = Field(default_factory=list, description="Tables this role can access")
    denied_tables: List[str] = Field(default_factory=list, description="Tables this role cannot access")
    permissions: List[str] = Field(default_factory=lambda: ["read"], description="Allowed permission types")


class RowPermission(BaseModel):
    """Row-level data permission."""
    user_id: str = Field(..., description="User identifier")
    table_name: str = Field(..., description="Table name")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Row filters, e.g., {'city': '北京'}")


class ColumnPermission(BaseModel):
    """Column-level field permission."""
    role: str = Field(..., description="User role")
    table_name: str = Field(..., description="Table name")
    masked_columns: List[str] = Field(default_factory=list, description="Columns to mask")
    hidden_columns: List[str] = Field(default_factory=list, description="Columns to hide completely")


class PermissionContext(BaseModel):
    """
    Full permission context for a user request.
    Combines role, row, and column permissions.
    """
    user_id: str
    role: str = "employee"
    data_scope: str = "department"

    # Row-level filters
    row_filters: Dict[str, Any] = Field(default_factory=dict)

    # Column-level restrictions
    masked_columns: Dict[str, List[str]] = Field(default_factory=dict)  # {table: [columns]}
    hidden_columns: Dict[str, List[str]] = Field(default_factory=dict)  # {table: [columns]}

    # Table access
    allowed_tables: List[str] = Field(default_factory=list)
    denied_tables: List[str] = Field(default_factory=list)

    # General permissions
    permissions: List[str] = Field(default_factory=lambda: ["read"])

    class Config:
        from_attributes = True

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def can_access_table(self, table_name: str) -> bool:
        """Check if user can access a table."""
        if table_name in self.denied_tables:
            return False
        if self.allowed_tables and table_name not in self.allowed_tables:
            return False
        return True

    def get_masked_columns_for_table(self, table_name: str) -> List[str]:
        """Get masked columns for a specific table."""
        return self.masked_columns.get(table_name, [])

    def get_hidden_columns_for_table(self, table_name: str) -> List[str]:
        """Get hidden columns for a specific table."""
        return self.hidden_columns.get(table_name, [])


class PermissionRule(BaseModel):
    """A single permission rule."""
    name: str
    description: str
    condition: Dict[str, Any] = Field(default_factory=dict)
    effect: str = Field(..., description="allow or deny")


class PermissionConfig(BaseModel):
    """Full permission configuration."""
    roles: Dict[str, RolePermission] = Field(default_factory=dict)
    row_permissions: Dict[str, List[RowPermission]] = Field(default_factory=dict)
    column_permissions: Dict[str, List[ColumnPermission]] = Field(default_factory=dict)