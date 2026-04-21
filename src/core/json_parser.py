"""
JSON Parser Module
Structured output enforcement with retry logic and validation.
"""

import json
import re
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, ValidationError
from loguru import logger


class StructuredOutputParser:
    """
    Ensures agent responses are valid JSON matching expected schemas.
    Includes cleanup, validation, and retry with feedback.
    """

    # Regex patterns for JSON extraction
    JSON_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*([\s\S]*?)\s*```')
    JSON_OBJECT_PATTERN = re.compile(r'\{[\s\S]*\}')

    @classmethod
    def extract_json(cls, raw_text: str) -> str:
        """
        Extract JSON from potentially noisy response text.
        Handles markdown code blocks, extra text, etc.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Empty response received")

        # Try to find JSON block in markdown code fence
        match = cls.JSON_BLOCK_PATTERN.search(raw_text)
        if match:
            return match.group(1).strip()

        # Try to find JSON object pattern
        match = cls.JSON_OBJECT_PATTERN.search(raw_text)
        if match:
            return match.group(0).strip()

        # Try to parse the whole text as JSON
        cleaned = raw_text.strip()
        if cleaned.startswith('{') or cleaned.startswith('['):
            return cleaned

        raise ValueError(f"Could not extract JSON from response: {raw_text[:100]}...")

    @classmethod
    def parse_and_validate(cls, raw_text: str, schema: Type[BaseModel]) -> BaseModel:
        """
        Parse raw text and validate against a Pydantic schema.

        Args:
            raw_text: Raw response from API
            schema: Pydantic model to validate against

        Returns:
            Validated Pydantic model instance

        Raises:
            ValueError: If parsing or validation fails
        """
        json_str = cls.extract_json(raw_text)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}\nContent: {json_str[:200]}...")
            raise ValueError(f"Invalid JSON: {str(e)}")

        try:
            return schema.model_validate(data)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}\nData: {json_str[:200]}...")
            raise ValueError(f"Schema validation failed: {str(e)}")

    @classmethod
    def parse_dict(cls, raw_text: str) -> Dict[str, Any]:
        """
        Parse raw text into a dictionary without schema validation.

        Args:
            raw_text: Raw response from API

        Returns:
            Dictionary with parsed data

        Raises:
            ValueError: If parsing fails
        """
        json_str = cls.extract_json(raw_text)

        try:
            data = json.loads(json_str)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}\nContent: {json_str[:200]}...")
            raise ValueError(f"Invalid JSON: {str(e)}")

    @classmethod
    def create_error_feedback(cls, error: str) -> str:
        """Create a feedback message for retry with error information."""
        return (
            f"Your previous response had the following error: {error}\n\n"
            f"Please provide a corrected response as valid JSON only. "
            f"Do not include any explanations or conversational text."
        )

    @classmethod
    def clean_response(cls, raw_text: str) -> str:
        """
        Clean response text by removing common conversational filler.

        Args:
            raw_text: Raw response from API

        Returns:
            Cleaned text ready for JSON parsing
        """
        # Remove leading/trailing whitespace
        cleaned = raw_text.strip()

        # Remove common conversational prefixes
        prefixes_to_remove = [
            "Here is the JSON:",
            "Here's the JSON:",
            "The JSON is:",
            "JSON response:",
            "Sure, here it is:",
            "Here you go:",
        ]
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()

        return cleaned