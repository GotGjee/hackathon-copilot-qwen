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

        # Build messages with JSON constraint
        messages = self._build_messages(system_prompt, user_prompt)
        messages.append({
            "role": "user",
            "content": "IMPORTANT: Respond with ONLY a valid JSON object. No markdown, no explanations, no code snippets. Start your response with { and end with }."
        })

        raw_response = await self.api_client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format="json_object",
        )

        # Parse JSON from response
        from src.core.json_parser import StructuredOutputParser
        try:
            data = StructuredOutputParser.parse_dict(raw_response)
        except ValueError as e:
            # Retry with error feedback
            feedback_msg = {
                "role": "user",
                "content": f"ERROR: Your previous response was not valid JSON. Please respond with ONLY a valid JSON object. Error: {str(e)}"
            }
            retry_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                feedback_msg,
            ]
            retry_response = await self.api_client.chat_completion(
                messages=retry_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format="json_object",
            )
            try:
                data = StructuredOutputParser.parse_dict(retry_response)
            except ValueError:
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