"""Utils module."""
from app.utils.logger import get_logger, setup_logger
from app.utils.exceptions import (
    AIAgentException,
    PermissionDeniedError,
    SQLInjectionError,
    InvalidQueryError,
    LLMError,
    DatabaseError,
    ToolExecutionError,
    SessionNotFoundError,
    UserNotFoundError,
    ConfigurationError,
)
from app.utils.helpers import (
    generate_session_id,
    generate_task_id,
    parse_time_range,
    format_number,
    format_percentage,
    flatten_dict,
    truncate_string,
    safe_json_serialize,
)

__all__ = [
    # Logger
    "get_logger",
    "setup_logger",
    # Exceptions
    "AIAgentException",
    "PermissionDeniedError",
    "SQLInjectionError",
    "InvalidQueryError",
    "LLMError",
    "DatabaseError",
    "ToolExecutionError",
    "SessionNotFoundError",
    "UserNotFoundError",
    "ConfigurationError",
    # Helpers
    "generate_session_id",
    "generate_task_id",
    "parse_time_range",
    "format_number",
    "format_percentage",
    "flatten_dict",
    "truncate_string",
    "safe_json_serialize",
]