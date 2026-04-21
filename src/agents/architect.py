"""
Architect Agent (Luna) - Tech Lead
Designs technical architecture for the selected project.
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient


class ArchitectResult(BaseModel):
    """Result from the Architect agent."""
    message: str
    file_structure: Dict[str, Any] = Field(default_factory=dict)
    tech_stack: List[Dict[str, str]] = Field(default_factory=list)
    api_endpoints: List[Dict[str, Any]] = Field(default_factory=list)
    data_models: List[Dict[str, Any]] = Field(default_factory=list)
    design_decisions: List[str] = Field(default_factory=list)
    closing_message: str


class ArchitectAgent(BaseAgent):
    """Luna - Tech Lead: Designs technical architecture."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "architect")

    async def design_architecture(
        self,
        title: str,
        description: str,
        key_features: List[str],
        constraints: str,
        tech_stack: List[str],
        milestones: List[Any],
    ) -> ArchitectResult:
        """Design technical architecture for the project."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        user_prompt = user_template.format(
            title=title,
            description=description,
            key_features=str(key_features),
            tech_stack=str(tech_stack),
            constraints=constraints,
            milestones=str([m.title for m in milestones]),
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
                    "message": "Architecture design complete",
                    "file_structure": {"src/": {"main.py": ""}},
                    "tech_stack": [{"name": "fastapi", "version": "0.115.0", "purpose": "Web framework"}],
                    "api_endpoints": [],
                    "data_models": [],
                    "design_decisions": ["FastAPI for async"],
                    "closing_message": "Ready to build!"
                }

        return ArchitectResult(
            message=data.get("message", ""),
            file_structure=data.get("file_structure", {}),
            tech_stack=data.get("tech_stack", []),
            api_endpoints=data.get("api_endpoints", []),
            data_models=data.get("data_models", []),
            design_decisions=data.get("design_decisions", []),
            closing_message=data.get("closing_message", ""),
        )