"""
Tests for API Client Module - Rate Limiter, Streaming, Validation.
"""

import os
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.api_client import RateLimiter


# ============================================================
# Rate Limiter Tests
# ============================================================

class TestRateLimiter:
    """Test the RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initial_call(self):
        """First call should not wait."""
        limiter = RateLimiter(calls_per_second=100.0)  # Fast rate for testing
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        # Should be nearly instant (within 100ms tolerance)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_delay(self):
        """Multiple rapid calls should enforce minimum interval."""
        limiter = RateLimiter(calls_per_second=10.0)  # 10 calls/sec = 100ms interval
        await limiter.acquire()  # First call
        start = time.monotonic()
        await limiter.acquire()  # Second call should wait
        elapsed = time.monotonic() - start
        # Should wait approximately 100ms
        assert elapsed >= 0.05  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_after_delay(self):
        """After waiting longer than interval, should allow immediately."""
        limiter = RateLimiter(calls_per_second=100.0)  # 10ms interval
        await limiter.acquire()
        await asyncio.sleep(0.05)  # Wait longer than interval
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_rate_limiter_multiple_acquires(self):
        """Test multiple consecutive acquires."""
        limiter = RateLimiter(calls_per_second=1000.0)  # Very fast
        for _ in range(5):
            await limiter.acquire()
        # Should complete without errors


# ============================================================
# API Client Validation Tests
# ============================================================

class TestQwenAPIClientValidation:
    """Test QwenAPIClient validation logic."""

    def test_missing_api_key_raises_error(self):
        """Should raise ValueError if no API key is provided."""
        from src.core.api_client import QwenAPIClient
        with patch.dict(os.environ, {"QWEN_API_KEY": ""}, clear=False):
            # Temporarily clear the env var
            original = os.environ.get("QWEN_API_KEY")
            try:
                os.environ["QWEN_API_KEY"] = ""
                with pytest.raises(ValueError, match="QWEN_API_KEY is required"):
                    QwenAPIClient()
            finally:
                if original is not None:
                    os.environ["QWEN_API_KEY"] = original

    def test_valid_api_key_accepted(self):
        """Should accept a valid API key."""
        from src.core.api_client import QwenAPIClient
        # This should not raise
        client = QwenAPIClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"
        # Cleanup
        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(client.close())
        except RuntimeError:
            pass


# ============================================================
# API Client Configuration Tests
# ============================================================

class TestQwenAPIClientConfig:
    """Test QwenAPIClient configuration."""

    def test_default_configuration(self):
        """Test default config values."""
        from src.core.api_client import QwenAPIClient
        client = QwenAPIClient(api_key="test-key")
        assert client.max_retries == 3
        assert client.timeout == 300.0
        assert client.default_model == "qwen3.6-plus"
        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(client.close())
        except RuntimeError:
            pass

    def test_custom_configuration(self):
        """Test custom config values."""
        from src.core.api_client import QwenAPIClient
        client = QwenAPIClient(
            api_key="test-key",
            base_url="https://custom.api.com",
            default_model="qwen3-coder",
            max_retries=5,
            timeout=60.0,
            rate_limit_calls_per_second=5.0,
        )
        assert client.max_retries == 5
        assert client.timeout == 60.0
        assert client.default_model == "qwen3-coder"
        assert client.base_url == "https://custom.api.com"
        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(client.close())
        except RuntimeError:
            pass

    def test_get_model_info(self):
        """Test model info retrieval."""
        from src.core.api_client import QwenAPIClient
        client = QwenAPIClient(api_key="test-key")
        info = client.get_model_info()
        assert "default_model" in info
        assert "base_url" in info
        assert info["default_model"] == "qwen3.6-plus"
        import asyncio
        try:
            asyncio.get_event_loop().run_until_complete(client.close())
        except RuntimeError:
            pass


# ============================================================
# Rate Limiter Edge Cases
# ============================================================

class TestRateLimiterEdgeCases:
    """Test edge cases for RateLimiter."""

    @pytest.mark.asyncio
    async def test_rate_limiter_very_high_rate(self):
        """Test with very high calls per second (minimal delay)."""
        limiter = RateLimiter(calls_per_second=10000.0)
        for _ in range(10):
            await limiter.acquire()
        # Should complete quickly

    @pytest.mark.asyncio
    async def test_rate_limiter_low_rate(self):
        """Test with very low calls per second (significant delay)."""
        limiter = RateLimiter(calls_per_second=1.0)  # 1 call per second
        await limiter.acquire()
        start = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - start
        # Should wait approximately 1 second (use lower threshold for CI)
        assert elapsed >= 0.5  # Allow tolerance for slow CI