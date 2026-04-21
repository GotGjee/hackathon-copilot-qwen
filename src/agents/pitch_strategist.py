"""
Pitch Strategist Agent (Nova) - Storyteller
Creates compelling narrative arc for the project pitch.
"""

from typing import List
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient
from src.core.state import PitchNarrative


class PitchResult(BaseModel):
    """Result from the Pitch Strategist agent."""
    message: str
    narrative: PitchNarrative
    key_messages: List[str] = Field(default_factory=list)
    closing_message: str


class PitchStrategistAgent(BaseAgent):
    """Nova - Storyteller: Creates compelling narratives."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "pitch_strategist")

    async def create_narrative(
        self,
        title: str,
        description: str,
        key_features: List[str],
        target_users: str,
    ) -> PitchResult:
        """Create a compelling narrative for the project pitch."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        user_prompt = user_template.format(
            title=title,
            description=description,
            key_features=str(key_features),
            target_users=target_users,
        )

        raw_response = await self._call_api(user_prompt, system_prompt)

        from src.core.json_parser import StructuredOutputParser
        try:
            data = StructuredOutputParser.parse_dict(raw_response)
        except ValueError:
            narrative = PitchNarrative(
                problem=f"Users struggle with {title}",
                solution=f"Our solution: {description}",
                demo_plan="Show the main features",
                impact="This will help many users",
                future_vision="Expand to more features",
            )
            return PitchResult(
                message="Narrative created",
                narrative=narrative,
                key_messages=["Problem", "Solution", "Demo"],
                closing_message="Ready to pitch!",
            )

        narrative_data = data.get("narrative", {})
        narrative = PitchNarrative(
            problem=narrative_data.get("problem", ""),
            solution=narrative_data.get("solution", ""),
            demo_plan=narrative_data.get("demo_plan", ""),
            impact=narrative_data.get("impact", ""),
            future_vision=narrative_data.get("future_vision", ""),
        )

        return PitchResult(
            message=data.get("message", ""),
            narrative=narrative,
            key_messages=data.get("key_messages", []),
            closing_message=data.get("closing_message", ""),
        )