"""
Dialogue Loop Module
Enables multi-turn agent-to-agent dialogue for better decision making.
Agents can debate, discuss, and refine ideas before finalizing.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class DialogueTurn:
    """A single turn in a dialogue between agents."""
    agent_type: str
    agent_name: str
    emoji: str
    role: str
    message: str
    turn_number: int


@dataclass
class DialogueHistory:
    """Complete history of a multi-turn dialogue."""
    topic: str
    turns: List[DialogueTurn] = field(default_factory=list)
    max_turns: int = 3
    is_complete: bool = False
    
    def add_turn(self, agent_type: str, agent_name: str, emoji: str, role: str, message: str):
        """Add a new turn to the dialogue."""
        turn = DialogueTurn(
            agent_type=agent_type,
            agent_name=agent_name,
            emoji=emoji,
            role=role,
            message=message,
            turn_number=len(self.turns) + 1,
        )
        self.turns.append(turn)
        if len(self.turns) >= self.max_turns:
            self.is_complete = True
    
    def get_formatted_history(self) -> str:
        """Format the dialogue history as a readable string."""
        lines = [f"📝 **Previous Dialogue on: {self.topic}**\n"]
        for turn in self.turns:
            lines.append(
                f"{turn.emoji} **{turn.agent_name}** ({turn.role}): {turn.message}"
            )
        return "\n\n".join(lines)
    
    def get_last_message(self) -> Optional[str]:
        """Get the last message in the dialogue."""
        if self.turns:
            return self.turns[-1].message
        return None
    
    def get_messages_by_agent(self, agent_type: str) -> List[str]:
        """Get all messages from a specific agent."""
        return [t.message for t in self.turns if t.agent_type == agent_type]


class DialogueManager:
    """
    Manages multi-turn dialogues between agents.
    Used for idea refinement, architecture review, and code critique discussions.
    """
    
    def __init__(self, max_turns: int = 3):
        self.max_turns = max_turns
        self._active_dialogues: Dict[str, DialogueHistory] = {}
    
    def start_dialogue(self, dialogue_id: str, topic: str) -> DialogueHistory:
        """Start a new dialogue."""
        dialogue = DialogueHistory(topic=topic, max_turns=self.max_turns)
        self._active_dialogues[dialogue_id] = dialogue
        return dialogue
    
    def get_dialogue(self, dialogue_id: str) -> Optional[DialogueHistory]:
        """Get an active dialogue."""
        return self._active_dialogues.get(dialogue_id)
    
    def complete_dialogue(self, dialogue_id: str) -> Optional[str]:
        """Complete a dialogue and return the summary."""
        dialogue = self._active_dialogues.get(dialogue_id)
        if dialogue:
            dialogue.is_complete = True
            return dialogue.get_formatted_history()
        return None
    
    def create_system_prompt_with_context(
        self,
        base_system_prompt: str,
        dialogue: DialogueHistory,
        responding_agent_type: str,
    ) -> str:
        """Create a system prompt that includes dialogue context."""
        context = f"""
{base_system_prompt}

PREVIOUS DIALOGUE CONTEXT:
The team has been discussing: {dialogue.topic}

Here's what has been said so far:
{dialogue.get_formatted_history()}

Your role in this dialogue:
- Respond to the points made by other agents
- Add your professional perspective
- Either agree with reasoning, disagree with alternatives, or build upon ideas
- Keep your response concise and focused
"""
        return context
    
    def create_user_prompt_with_feedback(
        self,
        base_user_prompt: str,
        user_feedback: Optional[str] = None,
        dialogue: Optional[DialogueHistory] = None,
    ) -> str:
        """Create a user prompt that incorporates user feedback and dialogue context."""
        prompt = base_user_prompt
        
        if dialogue and dialogue.turns:
            prompt += f"""

🔄 TEAM DIALOGUE CONTEXT:
Your team has been discussing this topic. Here's the dialogue history:
{dialogue.get_formatted_history()}

Please consider what your teammates have said and respond accordingly.
Respond to their points and either agree, disagree with reasoning, or build upon their ideas.
"""
        
        if user_feedback:
            prompt += f"""

👤 HUMAN FEEDBACK:
The human reviewer has provided the following feedback:
"{user_feedback}"

Please incorporate this feedback into your response. Address the concerns raised
and adjust your output accordingly.
"""
        
        return prompt


def create_debate_prompt(
    topic: str,
    agent_type: str,
    agent_name: str,
    emoji: str,
    role: str,
    opposing_view: str,
    opposing_agent_name: str,
    user_feedback: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Create a prompt for agent to respond in a debate.
    
    Args:
        topic: The debate topic
        agent_type: Type of the responding agent
        agent_name: Name of the responding agent
        emoji: Emoji for the agent
        role: Role of the agent
        opposing_view: The opposing agent's view to respond to
        opposing_agent_name: Name of the opposing agent
        user_feedback: Optional human feedback to incorporate
        
    Returns:
        List of messages for API call
    """
    system_prompt = f"""You are {agent_name} ({role}), participating in a team debate about: {topic}

Your personality and perspective:
- You are {role} with expertise in your domain
- You have your own opinions but are open to discussion
- You respond professionally and constructively

DEBATE RULES:
1. Acknowledge {opposing_agent_name}'s points
2. State your position clearly (agree, disagree, or partially agree)
3. Provide reasoning for your position
4. Suggest alternatives or improvements if you disagree
5. Keep your response focused and concise (max 3-4 sentences)
"""
    
    user_prompt = f"""🎯 Topic: {topic}

{opposing_agent_name}'s view:
{opposing_view}

Please respond to {opposing_agent_name}'s points. What do you think?
"""
    
    if user_feedback:
        user_prompt += f"""

👤 Human Feedback to Consider:
"{user_feedback}"

Please also address the human's feedback in your response.
"""
    
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


async def run_agent_dialogue(
    api_client,
    agent_instance,
    dialogue: DialogueHistory,
    topic: str,
    user_prompt: str,
    system_prompt: str,
    max_turns: int = 2,
) -> List[Dict[str, Any]]:
    """
    Run a multi-turn dialogue using the given agent.
    
    Args:
        api_client: The API client
        agent_instance: The agent instance
        dialogue: The dialogue history to add turns to
        topic: Topic of dialogue
        user_prompt: Base user prompt
        system_prompt: Base system prompt
        max_turns: Maximum number of turns
        
    Returns:
        List of dialogue turns with responses
    """
    results = []
    
    # Build initial prompt with dialogue context
    dialogue_manager = DialogueManager(max_turns=max_turns)
    enhanced_user_prompt = dialogue_manager.create_user_prompt_with_feedback(
        user_prompt,
        dialogue=dialogue if dialogue.turns else None,
    )
    
    try:
        # Get agent's response
        response = await api_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": enhanced_user_prompt},
            ],
            model=agent_instance.model,
            temperature=agent_instance.temperature,
            max_tokens=agent_instance.max_tokens,
        )
        
        # Add to dialogue
        dialogue.add_turn(
            agent_type=agent_instance.agent_type,
            agent_name=agent_instance.name,
            emoji=agent_instance.emoji,
            role=agent_instance.role,
            message=response,
        )
        
        results.append({
            "agent_type": agent_instance.agent_type,
            "agent_name": agent_instance.name,
            "message": response,
        })
        
    except Exception as e:
        logger.error(f"Dialogue turn failed for {agent_instance.name}: {e}")
        results.append({
            "agent_type": agent_instance.agent_type,
            "agent_name": agent_instance.name,
            "message": f"[Error: {str(e)}]",
        })
    
    return results