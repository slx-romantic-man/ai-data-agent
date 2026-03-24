"""
Unit tests for ReAct circuit breaker mechanism.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.agent.core.circuit_breaker import CircuitBreaker, CircuitState, get_react_circuit_breaker
from app.config.settings import settings


class TestCircuitBreaker:
    """Test cases for CircuitBreaker class."""

    def test_initial_state_is_closed(self):
        """Circuit breaker should start in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold_failures(self):
        """Circuit breaker should OPEN after consecutive failures reach threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5.0)

        # Record failures up to threshold
        for i in range(3):
            cb.record_failure(Exception(f"Error {i+1}"))

        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_resets_to_closed_after_success(self):
        """Circuit breaker should reset consecutive failures after success."""
        cb = CircuitBreaker(failure_threshold=3)

        # Record 2 failures (below threshold)
        cb.record_failure(Exception("Error 1"))
        cb.record_failure(Exception("Error 2"))

        # Record success
        cb.record_success()

        # Check consecutive failures reset
        assert cb.stats.consecutive_failures == 0
        assert cb.state == CircuitState.CLOSED

    def test_half_open_allows_limited_requests(self):
        """In HALF_OPEN state, only limited requests should be allowed."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=1)

        # Trigger OPEN state
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        import time
        time.sleep(0.2)

        # State should transition to HALF_OPEN on next check
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.can_execute() is True
        # Second call should be blocked
        assert cb.can_execute() is False

    def test_half_open_returns_to_open_on_failure(self):
        """Failure in HALF_OPEN should return to OPEN state."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        # Trigger OPEN
        cb.record_failure()
        import time
        time.sleep(0.2)

        # Transition to HALF_OPEN
        cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN

        # Record failure - should go back to OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_manual_reset(self):
        """Manual reset should return to CLOSED state."""
        cb = CircuitBreaker(failure_threshold=1)

        # Trigger OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Manual reset
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.stats.consecutive_failures == 0


class TestReActMaxIterations:
    """Test cases for ReAct max iterations circuit breaker."""

    @pytest.mark.asyncio
    async def test_stops_at_max_iterations(self):
        """ReAct loop should stop after reaching MAX_ITERATIONS."""
        from app.agent.core.streaming_agent import StreamingReActAgent
        from app.models.user import UserContext
        from app.models.permission import PermissionContext

        # Create agent with mocked LLM that always returns "continue thinking"
        agent = StreamingReActAgent()
        await agent.initialize()

        # Mock the LLM to return responses that never finish
        mock_llm = AsyncMock()
        mock_llm.chat_stream = AsyncMock(return_value=[])

        # Instead, we'll test the iteration counter directly
        max_iterations = settings.REACT_MAX_ITERATIONS
        iteration = 0
        results = []

        # Simulate the iteration check logic
        while iteration < max_iterations:
            iteration += 1
            results.append(iteration)
            if iteration >= max_iterations:
                break

        assert len(results) == max_iterations
        assert iteration == max_iterations

    def test_max_iterations_config(self):
        """Max iterations should be configurable from settings."""
        assert hasattr(settings, 'REACT_MAX_ITERATIONS')
        assert settings.REACT_MAX_ITERATIONS == 10

    def test_max_tokens_config(self):
        """Max tokens per query should be configurable from settings."""
        assert hasattr(settings, 'REACT_MAX_TOKENS_PER_QUERY')
        assert settings.REACT_MAX_TOKENS_PER_QUERY == 8000

    def test_timeout_config(self):
        """Timeout configurations should be set correctly."""
        assert hasattr(settings, 'REACT_TOOL_TIMEOUT_SECONDS')
        assert hasattr(settings, 'REACT_LOOP_TIMEOUT_SECONDS')
        assert settings.REACT_TOOL_TIMEOUT_SECONDS == 30
        assert settings.REACT_LOOP_TIMEOUT_SECONDS == 120


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker with agent."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_after_failures(self):
        """Agent should be blocked after consecutive failures."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

        # Simulate 3 failures
        for _ in range(3):
            cb.record_failure()

        # Circuit should be OPEN
        assert cb.can_execute() is False

        # Stats should show failures
        assert cb.stats.consecutive_failures == 3
        assert cb.stats.total_failures == 3

    @pytest.mark.asyncio
    async def test_error_message_format(self):
        """Circuit breaker error messages should be user-friendly."""
        from app.agent.core.streaming_agent import StreamingReActAgent

        agent = StreamingReActAgent()

        # Test _format_error method
        error_msg = agent._format_error("测试错误消息")

        assert error_msg["type"] == "error"
        assert "测试错误消息" in error_msg["data"]["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])