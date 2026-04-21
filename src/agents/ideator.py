"""
Ideator Agent (Max) - Creative Director
Generates innovative project ideas based on hackathon theme and constraints.
"""

import json
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient
from src.core.state import Idea


class IdeatorResult(BaseModel):
    """Result from the Ideator agent."""
    message: str
    ideas: List[Idea] = Field(default_factory=list)
    closing_message: str


class IdeatorAgent(BaseAgent):
    """Max - Creative Director: Generates innovative project ideas."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "ideator")

    async def generate_ideas(
        self,
        theme: str,
        constraints: str,
    ) -> IdeatorResult:
        """Generate 3-5 project ideas based on theme and constraints."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        user_prompt = user_template.format(
            theme=theme,
            constraints=constraints,
        )

        # Call API with JSON response expectation
        raw_response = await self._call_api(user_prompt, system_prompt)

        # Parse JSON from response
        from src.core.json_parser import StructuredOutputParser
        try:
            data = StructuredOutputParser.parse_dict(raw_response)
        except ValueError:
            # Fallback: create a minimal result
            data = {
                "message": f"Here are some ideas for: {theme}",
                "ideas": [
                    {
                        "id": 1,
                        "title": f"{theme} Solution",
                        "description": "A solution based on the theme",
                        "key_features": ["Feature 1", "Feature 2"],
                        "tech_stack": ["Python", "FastAPI"],
                        "innovation_score": 7,
                        "target_users": "General users"
                    }
                ],
                "closing_message": "Let me know which one you like!"
            }

        # Convert ideas to Idea models
        ideas = []
        for idea_data in data.get("ideas", []):
            idea = Idea(
                id=idea_data.get("id", len(ideas) + 1),
                title=idea_data.get("title", "Untitled"),
                description=idea_data.get("description", ""),
                key_features=idea_data.get("key_features", []),
                tech_stack=idea_data.get("tech_stack", []),
                innovation_score=idea_data.get("innovation_score", 5),
                target_users=idea_data.get("target_users", ""),
            )
            ideas.append(idea)

        return IdeatorResult(
            message=data.get("message", ""),
            ideas=ideas,
            closing_message=data.get("closing_message", ""),
        )