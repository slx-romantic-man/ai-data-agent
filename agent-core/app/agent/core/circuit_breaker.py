"""
Circuit Breaker for ReAct loop protection.

Prevents cascading failures by tracking consecutive errors and
temporarily blocking requests when error threshold is exceeded.
"""
import time
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitStats:
    """Statistics for circuit breaker."""
    total_requests: int = 0
    total_failures: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None


class CircuitBreaker:
    """
    Circuit breaker for protecting ReAct loop from cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Requests blocked, waiting for recovery timeout
    - HALF_OPEN: Limited requests allowed to test recovery
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures to trigger OPEN state
            recovery_timeout: Seconds to wait before trying HALF_OPEN
            half_open_max_calls: Max calls allowed in HALF_OPEN state
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current state, with automatic recovery check."""
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._should_attempt_recovery():
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get circuit breaker statistics."""
        return self._stats

    def can_execute(self) -> bool:
        """
        Check if execution is allowed.

        Returns:
            True if execution is allowed, False if blocked
        """
        current_state = self.state

        if current_state == CircuitState.CLOSED:
            return True

        if current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

        # OPEN state
        return False

    def record_success(self) -> None:
        """Record a successful execution."""
        self._stats.total_requests += 1
        self._stats.consecutive_failures = 0
        self._stats.last_success_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Recovery successful, go back to CLOSED
            self._transition_to(CircuitState.CLOSED)
            logger.info("Circuit breaker recovered: HALF_OPEN -> CLOSED")

    def record_failure(self, error: Optional[Exception] = None) -> None:
        """
        Record a failed execution.

        Args:
            error: Optional exception that caused the failure
        """
        self._stats.total_requests += 1
        self._stats.total_failures += 1
        self._stats.consecutive_failures += 1
        self._stats.last_failure_time = time.time()

        error_msg = str(error) if error else "Unknown error"
        logger.warning(
            f"Circuit breaker recorded failure: "
            f"consecutive={self._stats.consecutive_failures}, "
            f"threshold={self.failure_threshold}, error={error_msg}"
        )

        if self._state == CircuitState.HALF_OPEN:
            # Failed during recovery, go back to OPEN
            self._transition_to(CircuitState.OPEN)
            logger.warning("Circuit breaker recovery failed: HALF_OPEN -> OPEN")

        elif self._state == CircuitState.CLOSED:
            if self._stats.consecutive_failures >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
                logger.warning(
                    f"Circuit breaker tripped: CLOSED -> OPEN "
                    f"(consecutive failures: {self._stats.consecutive_failures})"
                )

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_calls = 0
        logger.info("Circuit breaker reset to CLOSED")

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self._stats.last_failure_time is None:
            return True

        elapsed = time.time() - self._stats.last_failure_time
        return elapsed >= self.recovery_timeout

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.CLOSED:
            self._stats.consecutive_failures = 0
            self._half_open_calls = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0

        logger.info(f"Circuit breaker state change: {old_state.value} -> {new_state.value}")


# Global circuit breaker instance for ReAct loop
_react_circuit_breaker: Optional[CircuitBreaker] = None


def get_react_circuit_breaker() -> CircuitBreaker:
    """Get or create the global ReAct circuit breaker."""
    global _react_circuit_breaker
    if _react_circuit_breaker is None:
        from app.config.settings import settings
        _react_circuit_breaker = CircuitBreaker(
            failure_threshold=getattr(settings, 'REACT_CIRCUIT_FAILURE_THRESHOLD', 3),
            recovery_timeout=getattr(settings, 'REACT_CIRCUIT_RECOVERY_TIMEOUT', 30.0),
        )
    return _react_circuit_breaker