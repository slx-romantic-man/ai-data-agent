"""
Table metadata and schema definitions.
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ColumnType(str, Enum):
    """Column data types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"


class ColumnMetadata(BaseModel):
    """Metadata for a table column."""
    name: str = Field(..., description="Column name")
    type: ColumnType = Field(..., description="Column data type")
    nullable: bool = Field(default=True, description="Whether column can be null")
    primary_key: bool = Field(default=False, description="Whether column is primary key")
    description: str = Field(default="", description="Column description")
    is_sensitive: bool = Field(default=False, description="Whether column contains sensitive data")
    is_dimension: bool = Field(default=False, description="Whether column is a dimension")
    is_metric: bool = Field(default=False, description="Whether column is a metric")


class TableMetadata(BaseModel):
    """Metadata for a database table."""
    table_name: str = Field(..., description="Table name")
    schema: str = Field(default="public", description="Schema name")
    description: str = Field(default="", description="Table description")
    columns: List[ColumnMetadata] = Field(default_factory=list, description="Table columns")
    primary_key: List[str] = Field(default_factory=list, description="Primary key columns")
    foreign_keys: Dict[str, str] = Field(default_factory=dict, description="Foreign key relationships")
    indexes: List[str] = Field(default_factory=list, description="Index names")
    row_count: Optional[int] = Field(default=None, description="Approximate row count")
    last_updated: Optional[str] = Field(default=None, description="Last update timestamp")

    def get_column_names(self) -> List[str]:
        """Get list of column names."""
        return [col.name for col in self.columns]

    def get_dimension_columns(self) -> List[str]:
        """Get dimension column names."""
        return [col.name for col in self.columns if col.is_dimension]

    def get_metric_columns(self) -> List[str]:
        """Get metric column names."""
        return [col.name for col in self.columns if col.is_metric]

    def get_sensitive_columns(self) -> List[str]:
        """Get sensitive column names."""
        return [col.name for col in self.columns if col.is_sensitive]

    def to_schema_description(self) -> str:
        """Generate schema description for LLM."""
        columns_desc = []
        for col in self.columns:
            col_desc = f"  - {col.name}: {col.type.value}"
            if col.description:
                col_desc += f" ({col.description})"
            if col.primary_key:
                col_desc += " [PK]"
            columns_desc.append(col_desc)

        return f"""
TABLE {self.table_name} ({self.description or 'No description'}):
{chr(10).join(columns_desc)}
"""


class DatabaseMetadata(BaseModel):
    """Metadata for entire database."""
    database_name: str = Field(..., description="Database name")
    tables: Dict[str, TableMetadata] = Field(default_factory=dict, description="Table metadata")
    version: str = Field(default="1.0", description="Metadata version")
    updated_at: str = Field(default="", description="Last update timestamp")

    def get_table_names(self) -> List[str]:
        """Get list of table names."""
        return list(self.tables.keys())

    def get_table(self, table_name: str) -> Optional[TableMetadata]:
        """Get table metadata by name."""
        return self.tables.get(table_name)

    def to_schema_description(self, table_names: Optional[List[str]] = None) -> str:
        """Generate schema description for LLM."""
        tables = table_names or self.get_table_names()
        descriptions = []

        for table_name in tables:
            table = self.get_table(table_name)
            if table:
                descriptions.append(table.to_schema_description())

        return "\n".join(descriptions)