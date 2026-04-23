"""
API Client Module
Async wrapper for Qwen API calls with retry logic, rate limiting, and streaming support.
"""

import os
import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from datetime import datetime

import httpx
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class RateLimiter:
    """
    Simple token bucket rate limiter for API calls.
    Prevents hitting API rate limits by enforcing minimum delay between calls.
    """

    def __init__(self, calls_per_second: float = 10.0):
        self.min_interval = 1.0 / calls_per_second
        self._last_call_time: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until we can make a call without exceeding rate limit."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                await asyncio.sleep(wait_time)
            self._last_call_time = time.monotonic()


class QwenAPIClient:
    """
    Async API client for Qwen models.
    Handles authentication, retries, rate limiting, and request formatting.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 300.0,
        rate_limit_calls_per_second: float = 10.0,
    ):
        # Validate API key
        self.api_key = api_key or os.getenv("QWEN_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "QWEN_API_KEY is required. Set it in .env file or pass it directly."
            )

        self.base_url = base_url or os.getenv("QWEN_BASE_URL", "https://coding-intl.dashscope.aliyuncs.com/v1")
        self.default_model = default_model or os.getenv("DEFAULT_MODEL", "qwen3.6-plus")
        self.max_retries = max_retries
        self.timeout = timeout

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(calls_per_second=rate_limit_calls_per_second)

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self.timeout, connect=10.0),
        )

        # Request tracking for debugging
        self._request_count = 0
        self._total_tokens_used = 0

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[str] = None,
    ) -> str:
        """
        Send a chat completion request to Qwen API.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name (defaults to self.default_model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (e.g., 'json_object')

        Returns:
            The generated text content as string

        Raises:
            Exception: If API call fails after retries
        """
        # Apply rate limiting
        await self.rate_limiter.acquire()

        model_name = model or self.default_model
        self._request_count += 1

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,  # Explicitly disable streaming
        }

        if response_format:
            payload["response_format"] = {"type": response_format}

        for attempt in range(self.max_retries):
            try:
                response = await self._client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()

                # Track token usage if available
                usage = data.get("usage", {})
                if usage:
                    self._total_tokens_used += usage.get("total_tokens", 0)

                # Extract content from response
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                logger.debug(f"API response received (attempt {attempt + 1}), request #{self._request_count}")
                return content.strip()

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on attempt {attempt + 1}: {e.response.status_code} - {e.response.text}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except httpx.RequestError as e:
                logger.error(f"Request error on attempt {attempt + 1}: {repr(e)}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                raise

        raise Exception("API call failed after maximum retries")

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Send a chat completion request with streaming response.

        Yields:
            Chunks of text as they are generated by the model.

        Raises:
            Exception: If API call fails after retries
        """
        await self.rate_limiter.acquire()

        model_name = model or self.default_model
        self._request_count += 1

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if response_format:
            payload["response_format"] = {"type": response_format}

        for attempt in range(self.max_retries):
            try:
                async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line or line.strip() == "[DONE]":
                            continue

                        # SSE format: data: {...}
                        if line.startswith("data: "):
                            line = line[6:]

                        try:
                            data = json.loads(line)
                            # Extract content from streaming chunk
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            content = delta.get("content", "")

                            if content:
                                yield content

                                # Track usage if available
                                usage = data.get("usage", {})
                                if usage:
                                    self._total_tokens_used += usage.get("total_tokens", 0)
                        except json.JSONDecodeError:
                            continue

                    logger.debug(f"Stream complete (attempt {attempt + 1}), request #{self._request_count}")
                    return

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on attempt {attempt + 1}: {e.response.status_code}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

            except httpx.RequestError as e:
                logger.error(f"Request error on attempt {attempt + 1}: {repr(e)}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise Exception("API call failed after maximum retries")

    async def chat_completion_stream_to_string(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: Optional[str] = None,
    ) -> str:
        """
        Send a streaming request and collect all chunks into a single string.

        Returns:
            The complete generated text as a single string.
        """
        chunks = []
        async for chunk in self.chat_completion_stream(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        ):
            chunks.append(chunk)
        return "".join(chunks)

    async def chat_completion_with_structured_output(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request and parse JSON response.

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If response is not valid JSON
        """
        content = await self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Clean up markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {content[:200]}...")
            raise ValueError(f"Invalid JSON response from API: {str(e)}")

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the current model configuration."""
        return {
            "default_model": self.default_model,
            "base_url": self.base_url,
            "max_retries": str(self.max_retries),
            "timeout": str(self.timeout),
        }