"""
Custom exceptions for AI Data Agent.
"""
from typing import Optional, Any


class AIAgentException(Exception):
    """Base exception for AI Data Agent."""

    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


# ==================== Authentication & Permission ====================

class AuthenticationError(AIAgentException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed",
                 details: Optional[Any] = None):
        super().__init__(message, details)


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""

    def __init__(self, message: str = "Token has expired",
                 details: Optional[Any] = None):
        super().__init__(message, details)


class PermissionDeniedError(AIAgentException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Permission denied",
                 details: Optional[Any] = None):
        super().__init__(message, details)


# ==================== Database & SQL ====================

class DatabaseError(AIAgentException):
    """Raised when database operation fails."""

    def __init__(self, message: str = "Database operation failed",
                 details: Optional[Any] = None):
        super().__init__(message, details)


class RecordNotFoundError(DatabaseError):
    """Raised when a database record is not found."""

    def __init__(self, model: str, identifier: Any):
        super().__init__(
            f"{model} not found: {identifier}",
            {"model": model, "identifier": identifier}
        )


class QueryExecutionError(DatabaseError):
    """Raised when a database query execution fails."""

    def __init__(self, query: str, message: str = "Query execution failed",
                 details: Optional[Any] = None):
        super().__init__(f"{message}: {query[:100]}", details)


class SQLInjectionError(AIAgentException):
    """Raised when SQL injection attempt is detected."""

    def __init__(self, message: str = "Potential SQL injection detected",
                 details: Optional[Any] = None):
        super().__init__(message, details)


class InvalidQueryError(AIAgentException):
    """Raised when a query is invalid."""

    def __init__(self, message: str = "Invalid query",
                 details: Optional[Any] = None):
        super().__init__(message, details)


# ==================== Agent Runtime ====================

class AgentError(AIAgentException):
    """Base exception for agent-related errors."""

    def __init__(self, message: str = "Agent error",
                 details: Optional[Any] = None):
        super().__init__(message, details)


class MaxIterationsExceeded(AgentError):
    """Raised when agent exceeds maximum iterations."""

    def __init__(self, iterations: int, message: str = None):
        msg = message or f"Exceeded maximum iterations ({iterations})"
        super().__init__(msg, {"iterations": iterations})


class ToolTimeoutError(AgentError):
    """Raised when tool execution times out."""

    def __init__(self, tool_name: str, timeout: int):
        super().__init__(
            f"Tool '{tool_name}' timed out after {timeout}s",
            {"tool_name": tool_name, "timeout": timeout}
        )


class ToolExecutionError(AIAgentException):
    """Raised when tool execution fails."""

    def __init__(self, tool_name: str, message: str = "Tool execution failed",
                 details: Optional[Any] = None):
        self.tool_name = tool_name
        super().__init__(f"Tool '{tool_name}': {message}", details)


# ==================== LLM ====================

class LLMError(AIAgentException):
    """Raised when LLM request fails."""

    def __init__(self, message: str = "LLM request failed",
                 details: Optional[Any] = None):
        super().__init__(message, details)


class LLMRateLimitError(LLMError):
    """Raised when LLM rate limit is hit."""

    def __init__(self, message: str = "LLM rate limit exceeded",
                 details: Optional[Any] = None):
        super().__init__(message, details)


# ==================== External Services ====================

class ExternalAPIError(AIAgentException):
    """Raised when external API call fails."""

    def __init__(self, api_name: str, message: str = "External API call failed",
                 details: Optional[Any] = None):
        self.api_name = api_name
        super().__init__(f"API '{api_name}': {message}", details)


# ==================== Business Logic ====================

class InsufficientCreditsError(AIAgentException):
    """Raised when user has insufficient credits."""

    def __init__(self, current: int, required: int):
        super().__init__(
            f"Insufficient credits: {current} available, {required} required",
            {"current": current, "required": required}
        )


class ValidationError(AIAgentException):
    """Raised when validation fails."""

    def __init__(self, message: str = "Validation failed",
                 details: Optional[Any] = None):
        super().__init__(message, details)


# ==================== Session & User ====================

class SessionNotFoundError(AIAgentException):
    """Raised when session is not found."""

    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}",
                         {"session_id": session_id})


class UserNotFoundError(AIAgentException):
    """Raised when user is not found."""

    def __init__(self, user_id: str):
        super().__init__(f"User not found: {user_id}", {"user_id": user_id})


# ==================== Configuration ====================

class ConfigurationError(AIAgentException):
    """Raised when configuration is invalid."""

    def __init__(self, message: str = "Invalid configuration",
                 details: Optional[Any] = None):
        super().__init__(message, details)