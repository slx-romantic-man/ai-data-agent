"""
Schema loader for loading and caching database metadata.
"""
from typing import Dict, List, Optional, Any
import json

from app.access.metadata.table_metadata import (
    DatabaseMetadata,
    TableMetadata,
    ColumnMetadata,
    ColumnType,
)
from app.access.database import MySQLClient, PostgreSQLClient
from app.utils.logger import get_logger


logger = get_logger()


class SchemaLoader:
    """
    Loads and caches database schema metadata.
    """

    def __init__(
        self,
        db_client: Optional[Any] = None,
    ):
        self._db = db_client
        self._metadata_cache: Dict[str, DatabaseMetadata] = {}
        self._table_cache: Dict[str, TableMetadata] = {}

    async def init(self, db_client: Any):
        """Initialize with database client."""
        self._db = db_client

    async def load_schema(
        self,
        database_name: str = "default",
        refresh: bool = False,
    ) -> DatabaseMetadata:
        """
        Load database schema metadata.

        Args:
            database_name: Database name
            refresh: Whether to refresh cache

        Returns:
            DatabaseMetadata with all table information
        """
        if not refresh and database_name in self._metadata_cache:
            return self._metadata_cache[database_name]

        try:
            # Get all tables
            tables = await self._db.get_all_tables()
            table_metadata = {}

            for table_name in tables:
                table_meta = await self._load_table_metadata(table_name)
                table_metadata[table_name] = table_meta
                self._table_cache[table_name] = table_meta

            metadata = DatabaseMetadata(
                database_name=database_name,
                tables=table_metadata,
            )

            self._metadata_cache[database_name] = metadata
            return metadata

        except Exception as e:
            logger.error(f"Failed to load schema: {str(e)}")
            raise

    async def _load_table_metadata(self, table_name: str) -> TableMetadata:
        """Load metadata for a single table."""
        try:
            schema_info = await self._db.get_table_schema(table_name)

            columns = []
            primary_keys = []

            for col_info in schema_info:
                # Map database type to ColumnType
                db_type = col_info.get("data_type", "varchar").lower()
                col_type = self._map_column_type(db_type)

                # Check if primary key
                is_pk = col_info.get("column_key", "") == "PRI"
                if is_pk:
                    primary_keys.append(col_info["column_name"])

                # Detect if column is sensitive
                col_name_lower = col_info["column_name"].lower()
                is_sensitive = any(
                    pattern in col_name_lower
                    for pattern in ["phone", "email", "id_card", "password", "salary"]
                )

                # Detect if column is dimension or metric
                is_dimension = any(
                    pattern in col_name_lower
                    for pattern in ["id", "name", "type", "status", "city", "department", "date"]
                )
                is_metric = any(
                    pattern in col_name_lower
                    for pattern in ["amount", "count", "sum", "avg", "total", "price"]
                )

                column = ColumnMetadata(
                    name=col_info["column_name"],
                    type=col_type,
                    nullable=col_info.get("is_nullable", "YES") == "YES",
                    primary_key=is_pk,
                    description=col_info.get("column_comment", ""),
                    is_sensitive=is_sensitive,
                    is_dimension=is_dimension,
                    is_metric=is_metric,
                )
                columns.append(column)

            return TableMetadata(
                table_name=table_name,
                columns=columns,
                primary_key=primary_keys,
            )

        except Exception as e:
            logger.error(f"Failed to load table metadata for {table_name}: {str(e)}")
            raise

    def _map_column_type(self, db_type: str) -> ColumnType:
        """Map database type to ColumnType enum."""
        type_mapping = {
            "varchar": ColumnType.STRING,
            "char": ColumnType.STRING,
            "text": ColumnType.STRING,
            "string": ColumnType.STRING,
            "int": ColumnType.INTEGER,
            "integer": ColumnType.INTEGER,
            "bigint": ColumnType.INTEGER,
            "smallint": ColumnType.INTEGER,
            "tinyint": ColumnType.INTEGER,
            "float": ColumnType.FLOAT,
            "double": ColumnType.FLOAT,
            "decimal": ColumnType.FLOAT,
            "numeric": ColumnType.FLOAT,
            "boolean": ColumnType.BOOLEAN,
            "bool": ColumnType.BOOLEAN,
            "date": ColumnType.DATE,
            "datetime": ColumnType.DATETIME,
            "timestamp": ColumnType.DATETIME,
            "json": ColumnType.JSON,
        }

        # Remove length specifier
        base_type = db_type.split("(")[0].strip()

        return type_mapping.get(base_type, ColumnType.STRING)

    def get_table_metadata(self, table_name: str) -> Optional[TableMetadata]:
        """Get cached table metadata."""
        return self._table_cache.get(table_name)

    def get_schema_description(self, table_names: Optional[List[str]] = None) -> str:
        """Get schema description for SQL generation."""
        if not self._table_cache:
            return ""

        if table_names:
            tables = [
                self._table_cache[name]
                for name in table_names
                if name in self._table_cache
            ]
        else:
            tables = list(self._table_cache.values())

        return "\n".join(t.to_schema_description() for t in tables)

    def clear_cache(self):
        """Clear metadata cache."""
        self._metadata_cache.clear()
        self._table_cache.clear()


# Global schema loader instance
_schema_loader: Optional[SchemaLoader] = None


def get_schema_loader() -> SchemaLoader:
    """Get schema loader instance."""
    global _schema_loader
    if _schema_loader is None:
        _schema_loader = SchemaLoader()
    return _schema_loader