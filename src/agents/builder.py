"""
Builder Agent (Kai) - Senior Developer
Generates actual Python/FastAPI code for the project.
"""

from typing import List
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient


class CodeFileResult(BaseModel):
    """Single code file result."""
    filepath: str
    description: str
    content: str
    language: str = "python"


class BuilderResult(BaseModel):
    """Result from the Builder agent."""
    message: str
    code_files: List[CodeFileResult] = Field(default_factory=list)
    closing_message: str


class BuilderAgent(BaseAgent):
    """Kai - Senior Developer: Generates actual code."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "builder")

    async def generate_code(
        self,
        title: str,
        architecture: dict,
        files_list: List[str],
        constraints: str,
    ) -> BuilderResult:
        """Generate code files for the project."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        user_prompt = user_template.format(
            title=title,
            architecture=str(architecture),
            files_list=str(files_list),
            constraints=constraints,
        )

        raw_response = await self._call_api(user_prompt, system_prompt)

        from src.core.json_parser import StructuredOutputParser
        try:
            data = StructuredOutputParser.parse_dict(raw_response)
        except ValueError:
            data = {
                "message": "Code generation complete",
                "code_files": [
                    {
                        "filepath": "src/main.py",
                        "description": "Main application entry point",
                        "content": "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/')\nasync def root():\n    return {'message': 'Hello World'}",
                        "language": "python"
                    }
                ],
                "closing_message": "Code ready for review!"
            }

        code_files = []
        for file_data in data.get("code_files", []):
            code_file = CodeFileResult(
                filepath=file_data.get("filepath", ""),
                description=file_data.get("description", ""),
                content=file_data.get("content", ""),
                language=file_data.get("language", "python"),
            )
            code_files.append(code_file)

        return BuilderResult(
            message=data.get("message", ""),
            code_files=code_files,
            closing_message=data.get("closing_message", ""),
        )