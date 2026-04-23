"""
Tests for the JSON parser module.
Covers JSON extraction from LLM responses, markdown handling, and error cases.
"""

import pytest
import json

from src.core.json_parser import StructuredOutputParser


class TestStructuredOutputParser:
    """Tests for the StructuredOutputParser class."""

    def test_extract_valid_json(self):
        """Test extracting valid JSON string."""
        json_str = '{"key": "value", "number": 42}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["key"] == "value"
        assert data["number"] == 42

    def test_extract_json_with_list(self):
        """Test extracting JSON with list."""
        json_str = '{"items": [1, 2, 3], "name": "test"}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["items"] == [1, 2, 3]
        assert data["name"] == "test"

    def test_extract_json_with_nested_objects(self):
        """Test extracting JSON with nested objects."""
        json_str = '{"outer": {"inner": {"value": "deep"}}}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["outer"]["inner"]["value"] == "deep"

    def test_extract_markdown_code_block(self):
        """Test extracting JSON from markdown code block."""
        json_str = '```json\n{"key": "value"}\n```'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["key"] == "value"

    def test_extract_markdown_without_lang(self):
        """Test extracting JSON from markdown without language specifier."""
        json_str = '```\n{"key": "value"}\n```'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["key"] == "value"

    def test_extract_with_surrounding_text(self):
        """Test extracting JSON with surrounding text."""
        json_str = 'Here is the result:\n```json\n{"key": "value"}\n```\nDone!'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["key"] == "value"

    def test_extract_preserves_inner_braces(self):
        """Test that JSON with nested braces is extracted correctly."""
        json_str = '{"data": {"nested": {"value": 1}}}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["data"]["nested"]["value"] == 1

    def test_extract_truncated_json_raises_error(self):
        """Test that truncated JSON that can't be recovered raises an exception."""
        with pytest.raises(Exception):
            # Input with no valid JSON structure at all
            StructuredOutputParser.extract_json("just some random text with no braces")

    def test_extract_empty_string_raises_error(self):
        """Test that empty string raises an exception."""
        with pytest.raises(Exception):
            StructuredOutputParser.extract_json("")

    def test_parse_dict_valid(self):
        """Test parse_dict with valid dict string."""
        json_str = '{"name": "test", "value": 123}'
        result = StructuredOutputParser.parse_dict(json_str)
        assert isinstance(result, dict)
        assert result["name"] == "test"

    def test_parse_dict_with_markdown(self):
        """Test parse_dict with markdown wrapper."""
        json_str = '```json\n{"name": "test"}\n```'
        result = StructuredOutputParser.parse_dict(json_str)
        assert result["name"] == "test"

    def test_extract_json_with_unicode(self):
        """Test extracting JSON with unicode characters."""
        json_str = '{"name": "สุรเดช", "emoji": "🧠"}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["name"] == "สุรเดช"
        assert data["emoji"] == "🧠"

    def test_extract_json_with_special_chars(self):
        """Test extracting JSON with special characters."""
        json_str = '{"path": "src/core/file.py", "code": "x = 1 + 2"}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["path"] == "src/core/file.py"

    def test_extract_json_array(self):
        """Test extracting JSON array."""
        text = '[1, 2, 3]'
        result = StructuredOutputParser.extract_json(text)
        data = json.loads(result)
        assert data == [1, 2, 3]

    def test_extract_json_with_escaped_chars(self):
        """Test extracting JSON with escaped characters."""
        json_str = '{"message": "Hello\\nWorld", "quote": "He said \\"hi\\""}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert "Hello" in data["message"]

    def test_extract_with_complex_surrounding(self):
        """Test JSON extraction with complex surrounding text."""
        json_str = """Here's the analysis:
        
```json
{
    "feasibility": 8,
    "impact": 9,
    "recommendation": "proceed"
}
```

This looks good overall."""
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["feasibility"] == 8
        assert data["impact"] == 9
        assert data["recommendation"] == "proceed"

    def test_extract_json_with_null_values(self):
        """Test extracting JSON with null values."""
        json_str = '{"key": null, "other": "value"}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["key"] is None
        assert data["other"] == "value"

    def test_extract_json_with_boolean_values(self):
        """Test extracting JSON with boolean values."""
        json_str = '{"enabled": true, "disabled": false}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["enabled"] is True
        assert data["disabled"] is False

    def test_extract_json_with_float_values(self):
        """Test extracting JSON with float values."""
        json_str = '{"score": 8.5, "ratio": 0.75}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["score"] == 8.5
        assert data["ratio"] == 0.75


class TestParserEdgeCases:
    """Edge case tests for JSON parser."""

    def test_extract_json_with_whitespace(self):
        """Test extracting JSON with extra whitespace."""
        json_str = '  {  "key"  :  "value"  }  '
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["key"] == "value"

    def test_extract_json_multiline_string(self):
        """Test extracting JSON with multiline string in markdown."""
        json_str = '''```json
{
    "name": "test",
    "description": "A test project",
    "items": [
        {"id": 1, "name": "item1"},
        {"id": 2, "name": "item2"}
    ]
}
```'''
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data["name"] == "test"
        assert len(data["items"]) == 2

    def test_extract_json_empty_object(self):
        """Test extracting empty JSON object."""
        json_str = '{}'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data == {}

    def test_extract_json_empty_array(self):
        """Test extracting empty JSON array."""
        json_str = '[]'
        result = StructuredOutputParser.extract_json(json_str)
        data = json.loads(result)
        assert data == []

    def test_clean_response(self):
        """Test clean_response method."""
        raw = "Here is the JSON:\n```json\n{\"key\": \"value\"}\n```"
        cleaned = StructuredOutputParser.clean_response(raw)
        assert '{"key"' in cleaned

    def test_create_error_feedback(self):
        """Test create_error_feedback method."""
        feedback = StructuredOutputParser.create_error_feedback("Test error")
        assert "Test error" in feedback
        assert "valid JSON" in feedback