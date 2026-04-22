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
            json_str = match.group(1).strip()
            # Verify this is complete JSON by checking brace balance
            if cls._is_balanced(json_str):
                return json_str

        # Try to find JSON object pattern and extract complete JSON
        # by finding the outermost braces
        result = cls._extract_complete_json(raw_text)
        if result:
            return result

        # Try to parse the whole text as JSON
        cleaned = raw_text.strip()
        if cleaned.startswith('{') or cleaned.startswith('['):
            return cleaned

        raise ValueError(f"Could not extract JSON from response: {raw_text[:100]}...")

    @classmethod
    def _is_balanced(cls, text: str) -> bool:
        """Check if braces are balanced in the text."""
        count = 0
        in_string = False
        escape_next = False
        for char in text:
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    count += 1
                elif char == '}':
                    count -= 1
        return count == 0

    @classmethod
    def _extract_complete_json(cls, raw_text: str) -> Optional[str]:
        """
        Extract complete JSON by finding matching braces.
        Handles nested JSON within string values.
        If JSON is truncated, tries to close it.
        """
        # Find the first opening brace
        start_idx = raw_text.find('{')
        if start_idx == -1:
            return None

        # Count braces to find the matching closing brace
        brace_count = 0
        in_string = False
        escape_next = False
        last_string_end = -1
        for i, char in enumerate(raw_text[start_idx:], start_idx):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                if not in_string:
                    last_string_end = i
                continue
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return raw_text[start_idx:i+1]

        # If we get here, JSON is truncated. Try to close it.
        if brace_count > 0:
            # Close any open string first
            result = raw_text[start_idx:]
            if in_string:
                result = result[:last_string_end - start_idx + 1] + '"'
                in_string = False
            # Close open braces
            while brace_count > 0:
                result += '}'
                brace_count -= 1
            return result

        return None

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
        # Clean the response first
        cleaned = cls.clean_response(raw_text)
        
        json_str = cls.extract_json(cleaned)

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
        Clean response text by removing common conversational filler and code fragments.

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

        # Remove Python code fragments that sometimes appear before JSON
        # Look for patterns like "):\n" or lines that start with code-like content
        lines = cleaned.split('\n')
        json_start_idx = -1
        
        # Find the first line that starts with { or [
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('{') or stripped.startswith('['):
                json_start_idx = i
                break
        
        if json_start_idx >= 0:
            # Reconstruct from the JSON start line
            cleaned = '\n'.join(lines[json_start_idx:])
        
        # Remove markdown code block markers if present
        if cleaned.startswith('```'):
            # Skip the first line (```)
            lines = cleaned.split('\n')
            if len(lines) > 1:
                cleaned = '\n'.join(lines[1:])
        
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3].rstrip()
        
        # Remove any text before the first { or [
        first_brace = cleaned.find('{')
        first_bracket = cleaned.find('[')
        
        if first_brace >= 0 or first_bracket >= 0:
            start = min(
                idx for idx in [first_brace, first_bracket] if idx >= 0
            )
            cleaned = cleaned[start:]

        return cleaned