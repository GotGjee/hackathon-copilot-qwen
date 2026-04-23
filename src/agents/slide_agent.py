"""
Slide Agent (อรุณี) - Presentation Designer
Creates detailed slide deck outline for the hackathon pitch.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient
from src.core.state import Slide, ColorPalette, FontStyle, ImageSuggestion


class DetailedSlideData(BaseModel):
    """Detailed slide data from the API response."""
    slide_number: int
    title: str
    subtitle: str
    bullet_points: List[str] = Field(default_factory=list)
    visual_suggestion: str
    design_note: str
    layout_type: str = "two-column"
    content_sections: List[str] = Field(default_factory=list)
    icon_suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    background_style: str = "solid"
    color_overrides: Optional[Dict[str, str]] = None
    animation_notes: str = ""
    speaker_script: str = ""
    estimated_duration_seconds: int = 30
    canva_template_hint: str = ""


class SlideDeckDesign(BaseModel):
    """Complete slide deck design from the API."""
    slides: List[DetailedSlideData]
    design_theme: str = "modern"
    color_palette: Dict[str, str] = Field(default_factory=dict)
    font_style: Optional[Dict[str, Any]] = None
    transition_style: Optional[Dict[str, Any]] = None
    total_slides: int = 0
    estimated_total_duration_minutes: float = 5.0
    design_guidelines: List[str] = Field(default_factory=list)


class SlideResult(BaseModel):
    """Result from the Slide agent."""
    slides: List[Slide] = Field(default_factory=list)
    design_theme: str = "modern"
    color_palette: Optional[ColorPalette] = None
    font_style: Optional[FontStyle] = None
    total_slides: int = 0
    estimated_total_duration_minutes: float = 5.0
    design_guidelines: List[str] = Field(default_factory=list)


class SlideAgent(BaseAgent):
    """อรุณี - Presentation Designer: Creates detailed slide outlines."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "slide_agent")

    async def create_slides(
        self,
        title: str,
        narrative: Any,
    ) -> SlideResult:
        """Create detailed slide deck outline for the pitch."""
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
            return self._parse_detailed_response(data)
        except ValueError:
            return self._create_fallback_result(title)

    def _parse_detailed_response(self, data: dict) -> SlideResult:
        """Parse the detailed API response."""
        slides = []
        for slide_data in data.get("slides", []):
            icon_suggestions = []
            for icon in slide_data.get("icon_suggestions", []):
                icon_suggestions.append(ImageSuggestion(
                    description=icon.get("description", ""),
                    icon_keywords=icon.get("icon_keywords", []),
                    image_type=icon.get("image_type", "icon"),
                    placement=icon.get("placement", "right"),
                    opacity=icon.get("opacity", 1.0),
                ))

            # Parse color overrides if present
            color_overrides = None
            if slide_data.get("color_overrides"):
                co = slide_data["color_overrides"]
                color_overrides = ColorPalette(
                    primary_color=co.get("primary_color", "#4A90E2"),
                    secondary_color=co.get("secondary_color", "#F5A623"),
                    background_color=co.get("background_color", "#FFFFFF"),
                    text_color=co.get("text_color", "#333333"),
                    accent_color=co.get("accent_color", "#7ED321"),
                    gradient_start=co.get("gradient_start", ""),
                    gradient_end=co.get("gradient_end", ""),
                )

            slide = Slide(
                slide_number=slide_data.get("slide_number", len(slides) + 1),
                title=slide_data.get("title", ""),
                subtitle=slide_data.get("subtitle", ""),
                bullet_points=slide_data.get("bullet_points", []),
                visual_suggestion=slide_data.get("visual_suggestion", ""),
                design_note=slide_data.get("design_note", ""),
                layout_type=slide_data.get("layout_type", "two-column"),
                content_sections=slide_data.get("content_sections", []),
                icon_suggestions=icon_suggestions,
                background_style=slide_data.get("background_style", "solid"),
                color_overrides=color_overrides,
                animation_notes=slide_data.get("animation_notes", ""),
                speaker_script=slide_data.get("speaker_script", ""),
                estimated_duration_seconds=slide_data.get("estimated_duration_seconds", 30),
                canva_template_hint=slide_data.get("canva_template_hint", ""),
            )
            slides.append(slide)

        # Parse deck-level design
        color_palette = None
        cp_data = data.get("color_palette")
        if cp_data and isinstance(cp_data, dict):
            color_palette = ColorPalette(
                primary_color=cp_data.get("primary_color", "#4A90E2"),
                secondary_color=cp_data.get("secondary_color", "#F5A623"),
                background_color=cp_data.get("background_color", "#FFFFFF"),
                text_color=cp_data.get("text_color", "#333333"),
                accent_color=cp_data.get("accent_color", "#7ED321"),
                gradient_start=cp_data.get("gradient_start", ""),
                gradient_end=cp_data.get("gradient_end", ""),
            )

        font_style = None
        font_data = data.get("font_style")
        if font_data and isinstance(font_data, dict):
            font_style = FontStyle(
                title_font=font_data.get("title_font", "Montserrat Bold"),
                subtitle_font=font_data.get("subtitle_font", "Open Sans"),
                body_font=font_data.get("body_font", "Roboto"),
                title_size=font_data.get("title_size", 36),
                body_size=font_data.get("body_size", 18),
                accent_size=font_data.get("accent_size", 14),
            )

        return SlideResult(
            slides=slides,
            design_theme=data.get("design_theme", "modern"),
            color_palette=color_palette,
            font_style=font_style,
            total_slides=len(slides),
            estimated_total_duration_minutes=data.get("estimated_total_duration_minutes", 5.0),
            design_guidelines=data.get("design_guidelines", []),
        )

    def _create_fallback_result(self, title: str) -> SlideResult:
        """Create a basic fallback slide result."""
        return SlideResult(
            slides=[
                Slide(
                    slide_number=1,
                    title=title,
                    subtitle="Hackathon Project",
                    bullet_points=["Project overview"],
                    visual_suggestion="Project logo",
                    design_note="Clean title slide",
                )
            ],
            design_theme="modern",
            total_slides=1,
        )