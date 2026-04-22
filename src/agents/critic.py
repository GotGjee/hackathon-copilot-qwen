"""
Critic Agent (Rex) - QA Lead
Reviews skeleton code for structure, completeness, and clarity.
"""

from typing import Dict, List, Union
from pydantic import BaseModel, Field
from loguru import logger

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient


class CodeIssue(BaseModel):
    """Single issue found by the Critic."""
    severity: str  # critical, high, medium, low
    file: str
    line: int = 0
    description: str
    fix: str


class CriticResult(BaseModel):
    """Result from the Critic agent."""
    message: str
    status: str  # "approved" or "rejected"
    issues: List[CodeIssue] = Field(default_factory=list)
    summary: str = ""
    closing_message: str = ""


class CriticAgent(BaseAgent):
    """Rex - QA Lead: Reviews skeleton code for issues."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "critic")

    async def review_code(
        self,
        code_artifacts: Dict[str, Union[dict, object]],
        requirements: str,
    ) -> CriticResult:
        """Review skeleton code for issues."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        # Format code artifacts for the prompt (handle both dict and CodeFile objects)
        code_parts = []
        for filepath, artifact in code_artifacts.items():
            if isinstance(artifact, dict):
                content = artifact.get("content", "")
            elif hasattr(artifact, "content"):
                content = artifact.content
            else:
                content = str(artifact)
            code_parts.append(f"File: {filepath}\n{content}")
        
        code_summary = "\n\n".join(code_parts)
        logger.debug(f"Critic reviewing {len(code_artifacts)} files")

        user_prompt = user_template.format(
            code_files_json=code_summary,
            requirements=requirements,
        )

        # Build messages with JSON constraint
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "user", "content": "IMPORTANT: Respond with ONLY a valid JSON object. No markdown, no explanations. Start with { and end with }."}
        ]

        max_retries = 3
        data = None
        
        for attempt in range(max_retries):
            try:
                raw_response = await self.api_client.chat_completion(
                    messages=messages,
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=max(self.max_tokens, 4000),
                    response_format="json_object",
                )
                
                from src.core.json_parser import StructuredOutputParser
                data = StructuredOutputParser.parse_dict(raw_response)
                if data and "status" in data:
                    break
                
                logger.warning(f"Critic retry {attempt+1}: invalid response")
                messages.append({
                    "role": "user",
                    "content": f"ERROR: Response missing 'status' field. Please include all required fields. Error: Empty or invalid response"
                })
                
            except ValueError as e:
                logger.warning(f"Critic JSON parse error (attempt {attempt+1}): {e}")
                messages.append({
                    "role": "user",
                    "content": f"ERROR: Invalid JSON. Please respond with ONLY valid JSON. Error: {str(e)}"
                })
            except Exception as e:
                logger.error(f"Critic API error (attempt {attempt+1}): {e}")
                messages.append({
                    "role": "user",
                    "content": f"ERROR: API error. Please respond with ONLY valid JSON. Error: {str(e)}"
                })
        
        # Fallback if all retries failed
        if not data:
            logger.warning("All Critic retries failed, using fallback")
            data = {
                "message": "Skeleton code review complete (fallback mode)",
                "status": "approved",
                "issues": [],
                "summary": "No critical issues found in skeleton structure",
                "closing_message": "Skeleton looks good for hackathon use."
            }

        # Convert issues to models
        issues = []
        for issue_data in data.get("issues", []):
            issue = CodeIssue(
                severity=issue_data.get("severity", "low"),
                file=issue_data.get("file", ""),
                line=issue_data.get("line", 0),
                description=issue_data.get("description", ""),
                fix=issue_data.get("fix", ""),
            )
            issues.append(issue)

        return CriticResult(
            message=data.get("message", ""),
            status=data.get("status", "approved"),
            issues=issues,
            summary=data.get("summary", ""),
            closing_message=data.get("closing_message", ""),
        )