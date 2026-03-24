"""
Unit tests for LLM client thread safety.
"""
import pytest
import threading
import time
from typing import List
from unittest.mock import patch, MagicMock


class TestLLMClientThreadSafety:
    """Test cases for LLM client thread safety."""

    def test_get_llm_returns_same_instance(self):
        """get_llm() should return the same instance on multiple calls."""
        from app.config.llm_config import get_llm, _llm_client

        # Reset the global client for clean test
        import app.config.llm_config as llm_module
        llm_module._llm_client = None

        client1 = get_llm()
        client2 = get_llm()
        client3 = get_llm()

        assert client1 is client2
        assert client2 is client3

    def test_concurrent_get_llm_returns_same_instance(self):
        """Concurrent calls to get_llm() should all return the same instance."""
        from app.config.llm_config import get_llm

        # Reset the global client for clean test
        import app.config.llm_config as llm_module
        llm_module._llm_client = None

        results: List = []
        threads = []

        def get_client():
            client = get_llm()
            results.append(id(client))

        # Create 100 threads
        for _ in range(100):
            t = threading.Thread(target=get_client)
            threads.append(t)

        # Start all threads
        for t in threads:
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # All results should be the same (same object id)
        assert len(results) == 100
        assert len(set(results)) == 1, "All threads should get the same client instance"

    def test_client_lock_exists(self):
        """The client lock should exist for thread safety."""
        from app.config.llm_config import _client_lock

        assert _client_lock is not None
        assert isinstance(_client_lock, type(threading.Lock()))

    def test_double_check_locking_pattern(self):
        """Verify double-check locking pattern is implemented correctly."""
        from app.config.llm_config import get_llm

        # Reset the global client
        import app.config.llm_config as llm_module
        llm_module._llm_client = None

        # First call should create the client
        client1 = get_llm()
        assert client1 is not None

        # Second call should return the same client without creating a new one
        # We can verify this by checking the id
        client2 = get_llm()
        assert id(client1) == id(client2)

    def test_client_type_is_correct(self):
        """The client should be of the correct type based on provider."""
        from app.config.llm_config import get_llm, BaseLLMClient

        client = get_llm()

        # Should be an instance of BaseLLMClient
        assert isinstance(client, BaseLLMClient)

    @patch('app.config.llm_config.settings')
    def test_client_created_with_correct_config(self, mock_settings):
        """Client should be created with correct configuration."""
        from app.config.llm_config import get_llm_client

        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.LLM_API_KEY = "test-key"
        mock_settings.LLM_API_BASE = "https://api.openai.com/v1"
        mock_settings.LLM_MODEL = "gpt-4"
        mock_settings.LLM_TEMPERATURE = 0.1
        mock_settings.LLM_MAX_TOKENS = 4096

        client = get_llm_client()

        assert client is not None
        assert client.api_key == "test-key"
        assert client.model == "gpt-4"

    def test_thread_safety_under_load(self):
        """Test thread safety under simulated load."""
        from app.config.llm_config import get_llm

        # Reset the global client
        import app.config.llm_config as llm_module
        llm_module._llm_client = None

        results = []
        errors = []

        def worker(worker_id: int):
            try:
                for i in range(10):
                    client = get_llm()
                    results.append((worker_id, i, id(client)))
                    time.sleep(0.001)  # Small delay to increase contention
            except Exception as e:
                errors.append((worker_id, str(e)))

        threads = []
        num_threads = 20

        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have no errors
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # All client ids should be the same
        client_ids = set(r[2] for r in results)
        assert len(client_ids) == 1, "All clients should have the same id"


class TestLLMClientInterface:
    """Test the LLM client interface."""

    def test_base_client_has_required_methods(self):
        """BaseLLMClient should have required abstract methods."""
        from app.config.llm_config import BaseLLMClient
        import inspect

        # Check that BaseLLMClient has the required abstract methods
        methods = [m[0] for m in inspect.getmembers(BaseLLMClient, inspect.isfunction)]

        assert 'chat' in methods or hasattr(BaseLLMClient, 'chat')
        assert 'chat_stream' in methods or hasattr(BaseLLMClient, 'chat_stream')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])