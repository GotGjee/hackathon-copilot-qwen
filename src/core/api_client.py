"""
API Client Module
Async wrapper for Qwen API calls with retry logic and rate limiting.
"""

import os
import asyncio
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class QwenAPIClient:
    """
    Async API client for Qwen models.
    Handles authentication, retries, and request formatting.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.getenv("QWEN_API_KEY", "")
        self.base_url = base_url or os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.default_model = default_model or os.getenv("DEFAULT_MODEL", "qwen-plus")
        self.max_retries = max_retries
        self.timeout = timeout

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self.timeout, connect=10.0),
        )

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
        model_name = model or self.default_model

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = {"type": response_format}

        for attempt in range(self.max_retries):
            try:
                response = await self._client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()

                # Extract content from response
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                logger.debug(f"API response received (attempt {attempt + 1})")
                return content.strip()

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error on attempt {attempt + 1}: {e.response.status_code} - {e.response.text}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except httpx.RequestError as e:
                logger.error(f"Request error on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                raise

        raise Exception("API call failed after maximum retries")

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