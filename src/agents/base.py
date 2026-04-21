"""
Base Agent Module
Abstract base class for all hackathon team agents.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import yaml

from src.core.api_client import QwenAPIClient


class BaseAgent(ABC):
    """
    Base class for all agents.
    Handles prompt loading, API communication, and response parsing.
    """

    def __init__(self, api_client: QwenAPIClient, agent_type: str):
        self.api_client = api_client
        self.agent_type = agent_type
        self.prompt_template = self._load_prompt_template(agent_type)
        self.agent_config = self._load_agent_config(agent_type)

    def _load_prompt_template(self, agent_type: str) -> Dict[str, Any]:
        """Load prompt template from YAML file."""
        try:
            with open(f"prompts/{agent_type}.yaml", "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {"system_prompt": "", "user_prompt_template": ""}

    def _load_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """Load agent configuration from config file."""
        try:
            with open("config/agents.yaml", "r") as f:
                config = yaml.safe_load(f)
                return config.get("agents", {}).get(agent_type, {})
        except FileNotFoundError:
            return {}

    @property
    def name(self) -> str:
        return self.agent_config.get("name", self.agent_type)

    @property
    def emoji(self) -> str:
        return self.agent_config.get("emoji", "🤖")

    @property
    def role(self) -> str:
        return self.agent_config.get("role", "Agent")

    @property
    def model(self) -> str:
        return self.agent_config.get("model", "qwen-plus")

    @property
    def temperature(self) -> float:
        return self.agent_config.get("temperature", 0.7)

    @property
    def max_tokens(self) -> int:
        return self.agent_config.get("max_tokens", 2000)

    def _build_messages(self, system_prompt: str, user_prompt: str) -> List[Dict[str, str]]:
        """Build message list for API call."""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    async def _call_api(self, user_prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call the API with the agent's configuration."""
        sys_prompt = system_prompt or self.prompt_template.get("system_prompt", "")
        messages = self._build_messages(sys_prompt, user_prompt)

        return await self.api_client.chat_completion(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    async def _call_api_json(self, user_prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Call the API and parse JSON response."""
        sys_prompt = system_prompt or self.prompt_template.get("system_prompt", "")
        messages = self._build_messages(sys_prompt, user_prompt)

        return await self.api_client.chat_completion_with_structured_output(
            messages=messages,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )