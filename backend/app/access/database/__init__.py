"""Database module."""
from app.access.database.connection import (
    DatabaseConnection,
    Base,
    get_db,
    close_db,
)
from app.access.database.mysql_client import MySQLClient, get_mysql_client
from app.access.database.postgres_client import PostgreSQLClient, get_postgres_client
from app.access.database.models import (
    UserAccount,
    UserQuota,
    CreditLog,
    Conversation,
    Message,
    APIConfig,
    ApiConfig,  # Alias for backward compatibility
    UserApiConfig,
    APICategory,
    UserAPIPermission,
    APICallLog,
)

__all__ = [
    "DatabaseConnection",
    "Base",
    "get_db",
    "close_db",
    "MySQLClient",
    "get_mysql_client",
    "PostgreSQLClient",
    "get_postgres_client",
    # Models
    "UserAccount",
    "UserQuota",
    "CreditLog",
    "Conversation",
    "Message",
    "APIConfig",
    "ApiConfig",  # Alias
    "UserApiConfig",
    "APICategory",
    "UserAPIPermission",
    "APICallLog",
]