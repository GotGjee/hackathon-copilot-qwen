"""
Script Agent (Nova - Script) - Speech Writer
Creates word-for-word speaker script for the hackathon pitch.
"""

from typing import Any, List
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient
from src.core.state import ScriptSection


class ScriptResult(BaseModel):
    """Result from the Script agent."""
    script: List[ScriptSection] = Field(default_factory=list)
    total_duration_seconds: int = 300
    estimated_word_count: int = 700


class ScriptAgent(BaseAgent):
    """Nova (Script) - Speech Writer: Creates speaker scripts."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "script_agent")

    async def create_script(
        self,
        title: str,
        slides: List[Any],
        narrative: Any,
    ) -> List[ScriptSection]:
        """Create speaker script for the pitch."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        slides_str = str([s.model_dump() if hasattr(s, 'model_dump') else str(s) for s in slides])
        narrative_str = str(narrative.model_dump()) if hasattr(narrative, 'model_dump') else str(narrative)

        user_prompt = user_template.format(
            title=title,
            slides_json=slides_str,
            narrative_json=narrative_str,
        )

        raw_response = await self._call_api(user_prompt, system_prompt)

        from src.core.json_parser import StructuredOutputParser
        try:
            data = StructuredOutputParser.parse_dict(raw_response)
        except ValueError:
            return [
                ScriptSection(
                    slide_number=1,
                    section="hook",
                    text=f"Welcome! Today we're presenting {title}.",
                    duration_seconds=30,
                    tone="energetic",
                    notes="Open with enthusiasm",
                )
            ]

        sections = []
        for section_data in data.get("script", []):
            section = ScriptSection(
                slide_number=section_data.get("slide_number", 1),
                section=section_data.get("section", ""),
                text=section_data.get("text", ""),
                duration_seconds=section_data.get("duration_seconds", 0),
                tone=section_data.get("tone", "normal"),
                notes=section_data.get("notes", ""),
            )
            sections.append(section)

        return sections