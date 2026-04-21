"""
Judge Agent (Sarah) - Pragmatic Lead
Evaluates and scores project ideas based on feasibility, impact, and complexity.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.core.api_client import QwenAPIClient
from src.core.state import Idea, IdeaEvaluation


class JudgeResult(BaseModel):
    """Result from the Judge agent."""
    message: str
    evaluations: List[IdeaEvaluation] = Field(default_factory=list)
    ranking: List[int] = Field(default_factory=list)
    closing_message: str


class JudgeAgent(BaseAgent):
    """Sarah - Pragmatic Lead: Evaluates and scores project ideas."""

    def __init__(self, api_client: QwenAPIClient):
        super().__init__(api_client, "judge")

    async def evaluate_ideas(
        self,
        ideas: List[Idea],
        constraints: str,
    ) -> JudgeResult:
        """Evaluate all ideas and return scored results."""
        template = self.prompt_template
        system_prompt = template.get("system_prompt", "")
        user_template = template.get("user_prompt_template", "")

        # Convert ideas to JSON for the prompt
        ideas_json = "[" + ", ".join([
            f'{{"id": {i.id}, "title": "{i.title}", "description": "{i.description}"}}'
            for i in ideas
        ]) + "]"

        user_prompt = user_template.format(
            ideas_json=ideas_json,
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
                # Fallback result
                evaluations = [
                    IdeaEvaluation(
                        idea_id=i.id,
                        idea_title=i.title,
                        scores={"feasibility": 5, "impact": 5, "technical_complexity": 5, "innovation": 5, "market_potential": 5},
                        total_score=5.0,
                        strengths=["Needs evaluation"],
                        risks=["Unknown"],
                        recommendation="Evaluate further",
                    )
                    for i in ideas
                ]
                return JudgeResult(
                    message="Evaluation needed",
                    evaluations=evaluations,
                    ranking=[i.id for i in ideas],
                    closing_message="Evaluation complete",
                )

        # Convert evaluations to models
        evaluations = []
        for eval_data in data.get("evaluations", []):
            scores = eval_data.get("scores", {})
            evaluation = IdeaEvaluation(
                idea_id=eval_data.get("idea_id", 0),
                idea_title=eval_data.get("idea_title", ""),
                scores=scores,
                total_score=eval_data.get("total_score", 0),
                strengths=eval_data.get("strengths", []),
                risks=eval_data.get("risks", []),
                recommendation=eval_data.get("recommendation", ""),
            )
            evaluations.append(evaluation)

        return JudgeResult(
            message=data.get("message", ""),
            evaluations=evaluations,
            ranking=data.get("ranking", []),
            closing_message=data.get("closing_message", ""),
        )