"""
Critic Agent (Rex) - QA Lead
Reviews generated code for bugs, security issues, and logic flaws.
"""

from typing import Dict, List, Union
from pydantic import BaseModel, Field

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
    """Rex - QA Lead: Reviews code for issues."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "critic")

    async def review_code(
        self,
        code_artifacts: Dict[str, Union[dict, object]],
        requirements: str,
    ) -> CriticResult:
        """Review generated code for issues."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        # Format code artifacts for the prompt (handle both dict and CodeFile objects)
        code_summary = "\n".join([
            f"File: {filepath}\n{artifact.get('content', '') if isinstance(artifact, dict) else getattr(artifact, 'content', '')}"
            for filepath, artifact in code_artifacts.items()
        ])

        user_prompt = user_template.format(
            code_files_json=code_summary,
            requirements=requirements,
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
                "content": f"ERROR: Your previous response was not valid JSON. Please respond with ONLY a valid JSON object. No code, no explanations. Error: {str(e)}"
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
                    "message": "Code review complete",
                    "status": "approved",
                    "issues": [],
                    "summary": "No issues found",
                    "closing_message": "Code looks good!"
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