"""
Planner Agent (Dave) - Project Manager
Breaks down project into milestones and tasks.
"""

from typing import List
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient
from src.core.state import Milestone


class PlannerResult(BaseModel):
    """Result from the Planner agent."""
    message: str
    milestones: List[Milestone] = Field(default_factory=list)
    total_hours: int = 36
    critical_path: List[int] = Field(default_factory=list)
    closing_message: str


class PlannerAgent(BaseAgent):
    """Dave - Project Manager: Creates milestone breakdowns."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "planner")

    async def create_milestones(
        self,
        title: str,
        description: str,
        key_features: List[str],
        constraints: str,
        tech_stack: List[str],
    ) -> PlannerResult:
        """Break down project into milestones."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        user_prompt = user_template.format(
            title=title,
            description=description,
            key_features=str(key_features),
            constraints=constraints,
            tech_stack=str(tech_stack),
        )

        raw_response = await self._call_api(user_prompt, system_prompt)

        from src.core.json_parser import StructuredOutputParser
        try:
            data = StructuredOutputParser.parse_dict(raw_response)
        except ValueError:
            data = {
                "message": "Planning complete",
                "milestones": [
                    {
                        "id": 1,
                        "title": "Setup",
                        "description": "Initial project setup",
                        "tasks": ["Create project structure"],
                        "estimated_hours": 2,
                        "dependencies": [],
                        "deliverables": ["Project skeleton"]
                    }
                ],
                "total_hours": 36,
                "critical_path": [1],
                "closing_message": "Let's get started!"
            }

        milestones = []
        for ms_data in data.get("milestones", []):
            milestone = Milestone(
                id=ms_data.get("id", len(milestones) + 1),
                title=ms_data.get("title", ""),
                description=ms_data.get("description", ""),
                tasks=ms_data.get("tasks", []),
                estimated_hours=ms_data.get("estimated_hours", 0),
                dependencies=ms_data.get("dependencies", []),
                deliverables=ms_data.get("deliverables", []),
            )
            milestones.append(milestone)

        return PlannerResult(
            message=data.get("message", ""),
            milestones=milestones,
            total_hours=data.get("total_hours", 36),
            critical_path=data.get("critical_path", []),
            closing_message=data.get("closing_message", ""),
        )