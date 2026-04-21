"""
Slide Agent (Nova - Slides) - Presentation Designer
Creates slide deck outline for the hackathon pitch.
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient
from src.core.state import Slide


class SlideResult(BaseModel):
    """Result from the Slide agent."""
    slides: List[Slide] = Field(default_factory=list)
    design_theme: str = "modern"


class SlideAgent(BaseAgent):
    """Nova (Slides) - Presentation Designer: Creates slide outlines."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "slide_agent")

    async def create_slides(
        self,
        title: str,
        narrative: Any,
    ) -> List[Slide]:
        """Create slide deck outline for the pitch."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        narrative_str = str(narrative.model_dump()) if hasattr(narrative, 'model_dump') else str(narrative)

        user_prompt = user_template.format(
            title=title,
            tagline=title,
            narrative_json=narrative_str,
        )

        raw_response = await self._call_api(user_prompt, system_prompt)

        from src.core.json_parser import StructuredOutputParser
        try:
            data = StructuredOutputParser.parse_dict(raw_response)
        except ValueError:
            return [
                Slide(
                    slide_number=1,
                    title=title,
                    subtitle="Hackathon Project",
                    bullet_points=["Project overview"],
                    visual_suggestion="Project logo",
                    design_note="Clean title slide",
                )
            ]

        slides = []
        for slide_data in data.get("slides", []):
            slide = Slide(
                slide_number=slide_data.get("slide_number", len(slides) + 1),
                title=slide_data.get("title", ""),
                subtitle=slide_data.get("subtitle", ""),
                bullet_points=slide_data.get("bullet_points", []),
                visual_suggestion=slide_data.get("visual_suggestion", ""),
                design_note=slide_data.get("design_note", ""),
            )
            slides.append(slide)

        return slides